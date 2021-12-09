import os
import re
import socket
import warnings
from itertools import chain
from pathlib import Path
from typing import Dict, Sequence, Tuple, Callable, Any, Union, NamedTuple
import importlib

from paramiko.config import SSHConfig
from pydantic import BaseModel, Extra, validator, root_validator
from yaml import safe_load
from connectome.storage import Storage, SSHLocation, Disk, RemoteStorage
from connectome.storage.config import HashConfig

from .utils import PathLike

CONFIG = '.bev.yml'


class ConfigError(Exception):
    pass


class HostName:
    key: str

    def match(self, name) -> bool:
        raise NotImplementedError

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, HostName):
            return v
        if isinstance(v, str):
            return StrHostName(v)

        assert isinstance(v, dict), f'Not a dict: {v}'
        assert len(v) == 1
        (k, v), = v.items()
        for kls in HostName.__subclasses__():
            if kls.key == k:
                return kls(v)

        raise ValueError(f'Invalid key "{k}" for hostname')


class StrHostName(HostName):
    key = 'str'

    def __init__(self, value):
        self.value = value

    def match(self, name) -> bool:
        return name == self.value


class RegexHostName(HostName):
    key = 'regex'

    def __init__(self, pattern):
        self.pattern = re.compile(pattern)

    def match(self, name) -> bool:
        return self.pattern.match(name) is not None


class LocationConfig(BaseModel):
    root: Path
    ssh: str = None

    @root_validator(pre=True)
    def resolve_deprecation(cls, values):
        if 'host' in values:
            assert 'ssh' not in values
            warnings.warn('The name "host" has been renamed to "ssh"')
            values['ssh'] = values.pop('host')

        return values

    class Config:
        extra = Extra.forbid


LocationConfigs = Tuple[LocationConfig, ...]


class StorageConfig(BaseModel):
    name: str
    default: Dict[str, Any] = None
    hostname: Tuple[HostName, ...] = ()
    storage: LocationConfigs
    cache: LocationConfigs = ()

    @validator('hostname', pre=True)
    def from_single(cls, v):
        if isinstance(v, (str, dict)):
            v = v,
        return v

    @validator('storage', 'cache', pre=True)
    def from_string(cls, v):
        if isinstance(v, str):
            v = v,
        return v

    @validator('storage', 'cache', each_item=True, pre=True)
    def add_defaults(cls, v, values):
        default = (values['default'] or {}).copy()
        if isinstance(v, str):
            v = {'root': v}
        assert isinstance(v, dict)
        default.update(v)
        return default

    class Config:
        extra = Extra.forbid


class ConfigMeta(BaseModel):
    choose: str = None
    fallback: str = None
    order: str = None
    hash: Union[str, HashConfig] = None

    @validator('hash', pre=True)
    def normalize_hash(cls, v):
        if isinstance(v, str):
            v = {'name': v}
        return v

    @root_validator(pre=True)
    def resolve_deprecation(cls, values):
        if 'default' in values:
            assert 'fallback' not in values
            warnings.warn('The name "default" has been renamed to "fallback"')
            values['fallback'] = values.pop('default')

        return values

    class Config:
        extra = Extra.forbid


class RepositoryConfig(BaseModel):
    local: StorageConfig
    remotes: Tuple[StorageConfig, ...]
    meta: ConfigMeta

    class Config:
        extra = Extra.forbid


class CacheIndex(NamedTuple):
    local: Sequence[PathLike]
    remote: Sequence[RemoteStorage] = ()


def load_config(config: Path) -> RepositoryConfig:
    with open(config, 'r') as file:
        return parse(config, safe_load(file))


def is_remove_available(location, config):
    # TODO: better way of handling missing hosts
    return location.ssh is not None and (config.lookup(location.ssh) != {
        'hostname': location.ssh} or location.ssh in config.get_hostnames())


def build_storage(root: Path) -> Tuple[Storage, CacheIndex]:
    config = load_config(root / CONFIG)
    meta = config.meta

    order_func: Callable[[Sequence[Disk]], Sequence[Disk]] = identity
    if meta.order is not None:
        path, attr = meta.order.rsplit('.', 1)
        order_func = getattr(importlib.import_module(path), attr)

    remote_storage, remote_cache = [], []
    # filter only available hosts
    # TODO: move to config?
    config_path = Path('~/.ssh/config').expanduser()
    if config_path.exists():
        with open(config_path) as f:
            ssh_config = SSHConfig()
            ssh_config.parse(f)

            for entry in config.remotes:
                for location in entry.storage:
                    if is_remove_available(location, ssh_config):
                        remote_storage.append(SSHLocation(location.ssh, location.root))

                for location in entry.cache:
                    if is_remove_available(location, ssh_config):
                        remote_cache.append(SSHLocation(location.ssh, location.root))

    loc = order_func([Disk(location.root) for location in config.local.storage])
    return Storage(loc, remote_storage), CacheIndex([c.root for c in config.local.cache], remote_cache)


def parse(root, config) -> RepositoryConfig:
    if not isinstance(config, dict):
        raise ConfigError('The config must be a dict')

    meta = ConfigMeta.parse_obj(config.pop('meta', {}))
    entries = {}
    for name, entry in config.items():
        if isinstance(entry, str):
            entry = {'storage': entry}
        if not isinstance(entry, dict):
            raise ConfigError('Each config entry must be either a dict or a string')
        if 'name' in entry:
            raise ConfigError('The key "name" is not available')
        entry = entry.copy()
        entry['name'] = name
        entries[name] = StorageConfig(**entry)

    fallback = None
    filter_func: Callable[[StorageConfig], bool] = default_choose
    if meta.choose is not None:
        path, attr = meta.choose.rsplit('.', 1)
        filter_func = getattr(importlib.import_module(path), attr)
    if meta.fallback is not None:
        fallback = meta.fallback
        if fallback not in entries:
            raise ConfigError(f'The fallback ({fallback}) is not present in the config {root}')

    if len(entries) == 1:
        local, = entries.values()
        remotes = []
    else:
        name = choose_local(entries.values(), filter_func, fallback)
        if name is None:
            raise ConfigError(f'No matching entry in config {root}')
        local = entries.pop(name)
        remotes = list(entries.values())

    return RepositoryConfig(local=local, remotes=remotes, meta=meta)


def choose_local(metas, func, default):
    for meta in metas:
        if func(meta):
            return meta.name

    return default


def default_choose(meta: StorageConfig):
    repo_key = 'BEV__REPOSITORY'
    if repo_key in os.environ:
        return meta.name == os.environ[repo_key]

    node = socket.gethostname()
    hosts = meta.hostname or [StrHostName(meta.name)]
    return any(h.match(node) for h in hosts)


def identity(x):
    return x


def _find_root(path, marker):
    path = Path(path).resolve()
    for parent in chain([path], path.parents):
        if (parent / marker).exists():
            return parent


def find_repo_root(path: PathLike):
    return _find_root(path, CONFIG)


def find_vcs_root(path: PathLike):
    return _find_root(path, '.git')
