import os
import platform
import socket
from itertools import chain
from pathlib import Path
from typing import NamedTuple, Dict, Sequence, Tuple, Callable, Optional
import importlib

from paramiko.config import SSHConfig
from yaml import safe_load

from connectome.storage import Storage, SSHLocation, Disk
from .utils import PathLike

CONFIG = '.bev.yml'


# TODO: pydantic
class LocationMeta(NamedTuple):
    root: str
    host: Optional[str] = None


class StorageMeta(NamedTuple):
    name: str
    locations: Sequence[LocationMeta]
    hostnames: Optional[Sequence[str]]
    cache: Optional[str]


def build_storage(root: Path) -> Tuple[Storage, str]:
    with open(root / CONFIG, 'r') as file:
        config = safe_load(file)

    entry, others = parse(config)

    remote = []
    # filter only available hosts
    # TODO: move to config?
    config_path = Path('~/.ssh/config').expanduser()
    if config_path.exists():
        with open(config_path) as f:
            config = SSHConfig()
            config.parse(f)

            remote = [
                SSHLocation(location.host, location.root)
                for name, meta in others.items() for location in meta.locations
                # TODO: better way of handling missing hosts
                if location.host is not None and (config.lookup(location.host) != {
                    'hostname': location.host} or location.host in config.get_hostnames())
            ]

    local = [Disk(location.root) for location in entry.locations]
    return Storage(local, remote), entry.cache


def parse(config) -> Tuple[StorageMeta, Dict[str, StorageMeta]]:
    filter_func: Callable[[StorageMeta], bool] = default_choose
    meta = config.pop('meta', {})
    assert set(meta) <= {'choose', 'default'}
    if 'choose' in meta:
        path, attr = meta.pop('choose').rsplit('.', 1)
        filter_func = getattr(importlib.import_module(path), attr)
    default_storage = meta.get('default')

    result = {}
    for name, meta in config.items():
        default = meta.pop('default', {})
        assert set(meta) <= {'storage', 'cache', 'hostname'}

        locations = []
        for location in meta['storage']:
            keys = default.copy()
            keys.update(location)
            locations.append(LocationMeta(**keys))

        hostname = meta.get('hostname')
        if isinstance(hostname, str):
            hostname = [hostname]

        result[name] = StorageMeta(name, locations, hostname, meta.get('cache'))

    if default_storage is not None and default_storage not in result:
        raise ValueError(f'The default storage ({default_storage}) is not present in the config')

    if len(result) == 1:
        entry, = result.values()
        result = {}
    else:
        name = choose_local(result.values(), filter_func) or default_storage
        if name is None:
            raise ValueError('No matching entry in config')

        entry = result.pop(name)

    return entry, result


def choose_local(metas, func) -> str:
    for meta in metas:
        if func(meta):
            return meta.name


def default_choose(meta: StorageMeta):
    repo_key = 'BEV__REPOSITORY'
    if repo_key in os.environ:
        return meta.name == os.environ[repo_key]

    node = socket.gethostname()
    hosts = meta.hostnames or [meta.name]
    return any(h == node for h in hosts)


def _find_root(path, marker):
    path = Path(path).resolve()
    for parent in chain([path], path.parents):
        if (parent / marker).exists():
            return parent


def find_repo_root(path: PathLike):
    return _find_root(path, CONFIG)


def find_vcs_root(path: PathLike):
    return _find_root(path, '.git')
