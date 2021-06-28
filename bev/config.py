import platform
from itertools import chain
from pathlib import Path
from typing import NamedTuple, Dict, Sequence, Tuple
import importlib

from paramiko.config import SSHConfig
from yaml import safe_load

from connectome.storage import Storage, SSHLocation, Disk
from .interface import Repository, PathLike
from .utils import RepositoryNotFoundError


# TODO: pydantic
class LocationMeta(NamedTuple):
    root: str
    host: str = None


class StorageMeta(NamedTuple):
    locations: Sequence[LocationMeta]
    cache: str = None


def build_storage(path: Path) -> Tuple[Storage, str]:
    with open(path, 'r') as file:
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
    filter_func = choose_by_hostname
    meta = config.pop('meta', {})
    assert set(meta) <= {'choose'}
    if 'choose' in meta:
        path, attr = meta.pop('choose').rsplit('.', 1)
        filter_func = getattr(importlib.import_module(path), attr)

    result = {}
    for name, meta in config.items():
        default = meta.pop('default', {})
        assert set(meta) <= {'storage', 'cache'}

        locations = []
        for location in meta['storage']:
            keys = default.copy()
            keys.update(location)
            locations.append(LocationMeta(**keys))

        result[name] = StorageMeta(locations, meta.get('cache'))

    if len(result) == 1:
        entry, = result.values()
        result = {}
    else:
        entry = result.pop(choose_local(result, filter_func))

    return entry, result


def choose_local(names, func):
    for name in names:
        if func(name):
            return name

    raise ValueError('No matching entry in config')


def choose_by_hostname(key):
    return key == platform.node()


CONFIG = '.bev.yml'


def get_current_repo(path: PathLike = '.') -> Repository:
    path = Path(path).resolve()
    for parent in chain([path], path.parents):
        config = parent / CONFIG
        if config.exists():
            storage, cache = build_storage(config)
            return Repository(parent, storage, cache)

    raise RepositoryNotFoundError(f'{CONFIG} files not found in current folder\'s parents')
