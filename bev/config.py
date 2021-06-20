import ast
import platform
from itertools import chain
from pathlib import Path
from typing import NamedTuple, Dict, Sequence, Tuple
import importlib

from connectome.storage import Storage, SSHLocation, Disk
from connectome.storage.locker import RedisLocker
from paramiko.config import SSHConfig
from redis import Redis
from yaml import safe_load
import humanfriendly

from .interface import Repository, PathLike


class LocationMeta(NamedTuple):
    root: str
    free: int = 0
    size: int = None
    host: str = None
    lock: str = None
    lock_prefix_size: int = 16


class CacheMeta(NamedTuple):
    root: str
    lock: str = None


class StorageMeta(NamedTuple):
    locations: Sequence[LocationMeta]
    cache: CacheMeta = None


def build_storage(path: Path) -> Tuple[Storage, CacheMeta]:
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

    local = []
    for location in entry.locations:
        local.append(Disk(
            location.root, location.free, location.size, locker=make_locker(location.lock),
            lock_prefix_size=location.lock_prefix_size
        ))

    return Storage(local, remote), entry.cache


def make_locker(locker):
    if locker is None:
        return

    locker = locker.strip()
    assert locker.endswith(')')
    idx = locker.index('(')
    name, args = locker[:idx], locker[idx:]
    # TODO: add real name detection
    assert name == 'Redis'
    url, prefix = ast.literal_eval(args)
    return RedisLocker(Redis(url), prefix, 10 * 60)


def parse(config) -> Tuple[StorageMeta, Dict[str, StorageMeta]]:
    filter_func = choose_by_hostname
    if '__filter__' in config:
        path, attr = config.pop('__filter__').rsplit('.', 1)
        filter_func = getattr(importlib.import_module(path), attr)

    result = {}
    for name, meta in config.items():
        default = meta.pop('default', {})
        locations = []

        for location in meta['storage']:
            keys = default.copy()
            keys.update(location)
            for k in ['size', 'free']:
                if k in keys:
                    keys[k] = humanfriendly.parse_size(keys[k])

            locations.append(LocationMeta(**keys))

        cache = None
        if 'cache' in meta:
            cache = CacheMeta(**meta['cache'])
        result[name] = StorageMeta(locations, cache)

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

    raise FileNotFoundError(f'{CONFIG} files not found in current folder\'s parents')
