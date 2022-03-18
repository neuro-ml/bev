import os
import re
import socket
from itertools import chain
from pathlib import Path
from typing import Dict, Sequence, Tuple, Callable, Any, Union, NamedTuple
import importlib

from paramiko.config import SSHConfig
from pydantic import BaseModel, Extra, validator, root_validator, ValidationError
from yaml import safe_load
from tarn import Storage, SSHLocation, Disk, RemoteStorage, StorageLevel
from tarn.config import HashConfig

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


class NoExtra(BaseModel):
    class Config:
        extra = Extra.forbid


class LocationConfig(NoExtra):
    root: Path
    ssh: str = None
    optional: bool = False

    @root_validator(pre=True)
    def from_string(cls, v):
        if isinstance(v, str):
            return cls(root=v)
        return v


class StorageLevelConfig(NoExtra):
    default: Dict[str, Any] = None
    locations: Sequence[LocationConfig]
    write: bool = True
    replicate: bool = True

    @root_validator(pre=True)
    def from_builtins(cls, v):
        if isinstance(v, dict):
            return v
        return cls(locations=v)

    @validator('default', pre=True, always=True)
    def fill(cls, v):
        if v is None:
            return {}
        return v

    @validator('locations', pre=True)
    def from_string(cls, v):
        if isinstance(v, str):
            v = v,
        return v

    @validator('locations', each_item=True, pre=True)
    def add_defaults(cls, v, values):
        default = (values['default'] or {}).copy()
        if isinstance(v, str):
            v = {'root': v}

        if default:
            assert isinstance(v, dict), type(v)
            default.update(v)
            return default

        return v

    @validator('locations')
    def to_tuple(cls, v):
        return tuple(v)


class StorageCluster(NoExtra):
    name: str
    default: Dict[str, Any] = None
    hostname: Sequence[HostName] = ()
    storage: Sequence[StorageLevelConfig]
    cache: Sequence[StorageLevelConfig] = ()

    @validator('hostname', pre=True)
    def from_single(cls, v):
        if isinstance(v, (str, dict, HostName)):
            v = v,
        return v

    @validator('storage', 'cache', pre=True)
    def from_string(cls, v, values):
        if isinstance(v, (str, dict, StorageLevelConfig, LocationConfig)):
            v = v,

        default = (values['default'] or {}).copy()
        # first try to interpret the entire storage as a single level
        try:
            return StorageLevelConfig(locations=v, default=default),
        except ValidationError:
            pass

        result = []
        for entry in v:
            if isinstance(entry, (str, LocationConfig)):
                entry = StorageLevelConfig(locations=entry, default=default)
            elif isinstance(entry, dict):
                local_entry = entry.copy()
                local_default = local_entry.pop('default', {}).copy()
                local_default.update(default)
                local_entry['default'] = local_default

                try:
                    entry = StorageLevelConfig(**local_entry)
                except ValidationError:
                    entry = StorageLevelConfig(locations=entry, default=default)

            result.append(entry)

        return tuple(result)


class ConfigMeta(NoExtra):
    choose: str = None
    fallback: str = None
    order: str = None
    hash: Union[str, HashConfig] = None

    @validator('hash', pre=True)
    def normalize_hash(cls, v):
        if isinstance(v, str):
            v = {'name': v}
        return v


class RepositoryConfig(NoExtra):
    local: StorageCluster
    remotes: Sequence[StorageCluster]
    meta: ConfigMeta


class CacheStorageIndex(NamedTuple):
    local: Sequence[StorageLevelConfig]
    remote: Sequence[RemoteStorage] = ()


def load_config(config: Path) -> RepositoryConfig:
    with open(config, 'r') as file:
        return parse(config, safe_load(file))


def is_remote_available(location, config):
    # TODO: better way of handling missing hosts
    return location.ssh is not None and (config.lookup(location.ssh) != {
        'hostname': location.ssh} or location.ssh in config.get_hostnames())


def build_storage(root: Path) -> Tuple[Storage, CacheStorageIndex]:
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
                for level in entry.storage:
                    for location in level.locations:
                        if is_remote_available(location, ssh_config):
                            remote_storage.append(SSHLocation(location.ssh, location.root))

                for level in entry.cache:
                    for location in level.locations:
                        if is_remote_available(location, ssh_config):
                            remote_cache.append(SSHLocation(location.ssh, location.root))

    storage = [
        StorageLevel(
            order_func([Disk(location.root) for location in level.locations]),
            write=level.write, replicate=level.replicate,
        )
        for level in _filter_levels(config.local.storage)
    ]
    return Storage(*storage, remote=remote_storage), CacheStorageIndex(
        tuple(_filter_levels(config.local.cache)), remote_cache)


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
        entries[name] = StorageCluster(**entry)

    fallback = None
    filter_func: Callable[[StorageCluster], bool] = default_choose
    if meta.choose is not None:
        path, attr = meta.choose.rsplit('.', 1)
        filter_func = getattr(importlib.import_module(path), attr)
    if meta.fallback is not None:
        fallback = meta.fallback
        if fallback not in entries:
            raise ConfigError(f'The fallback ({fallback}) is not present in the config {root}')

    if len(entries) == 1:
        local, = entries.values()
        remotes = ()
    else:
        name = choose_local(entries.values(), filter_func, fallback)
        if name is None:
            raise ConfigError(f'No matching entry in config {root}')
        local = entries.pop(name)
        remotes = tuple(entries.values())

    return RepositoryConfig(local=local, remotes=remotes, meta=meta)


def _filter_levels(levels):
    for level in levels:
        locations = [
            x for x in level.locations
            if not x.optional or x.root.exists()
        ]
        if locations:
            level = level.copy()
            level.locations = locations
            yield level


def choose_local(metas, func, default):
    for meta in metas:
        if func(meta):
            return meta.name

    return default


def default_choose(meta: StorageCluster):
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
