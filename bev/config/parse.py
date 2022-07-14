from pathlib import Path
from typing import Sequence, Tuple, Callable, NamedTuple
import importlib

from yaml import safe_load
from tarn import Storage, Disk, RemoteStorage

from .base import StorageLevelConfig, RepositoryConfig, ConfigMeta, StorageCluster
from .utils import CONFIG, identity, _filter_levels, choose_local, default_choose, wrap_levels
from ..exceptions import ConfigError


class CacheStorageIndex(NamedTuple):
    local: Sequence[StorageLevelConfig]
    remote: Sequence[RemoteStorage] = ()


def load_config(config: Path) -> RepositoryConfig:
    with open(config, 'r') as file:
        return parse(config, safe_load(file))


def build_storage(root: Path) -> Tuple[Storage, CacheStorageIndex]:
    config = load_config(root / CONFIG)
    meta = config.meta

    order_func: Callable[[Sequence[Disk]], Sequence[Disk]] = identity
    if meta.order is not None:
        path, attr = meta.order.rsplit('.', 1)
        order_func = getattr(importlib.import_module(path), attr)

    # filter only available remotes
    remote_storage, remote_cache = [], []
    for entry in config.remotes:
        for container, levels in zip((remote_storage, remote_cache), (entry.storage, entry.cache)):
            for level in levels:
                for location in level.locations:
                    for remote in location.remote:
                        remote = remote.build(location.root, location.optional)
                        if remote is not None:
                            container.append(remote)

    return Storage(*wrap_levels(config.local.storage, Disk, order_func), remote=remote_storage), CacheStorageIndex(
        tuple(_filter_levels(config.local.cache)), remote_cache)


def parse(root, config) -> RepositoryConfig:
    meta, entries = _parse(root, config, root)

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


def _parse(name, config, root):
    if not isinstance(config, dict):
        raise ConfigError(f'{name}: The config must be a dict')

    config = config.copy()
    meta = ConfigMeta.parse_obj(config.pop('meta', {}))
    # parse own items
    entries = {}
    for name, entry in config.items():
        if isinstance(entry, str):
            entry = {'storage': entry}
        if not isinstance(entry, dict):
            raise ConfigError(f'{name}: Each config entry must be either a dict or a string')
        if 'name' in entry:
            raise ConfigError(f'{name}: The key "name" is not available')
        entry = entry.copy()
        entry['name'] = name
        entries[name] = StorageCluster(**entry)

    # parse parents
    for parent in meta.include:
        # TODO: don't just discard the parent meta
        parent_root, parent_config = parent.read(root)
        if parent_config is None:
            if parent.optional:
                continue
            raise ConfigError(f'Parent config "{parent.value}" not found')

        _, items = _parse(parent.value, parent_config, parent_root)
        common = set(items) & set(entries)
        if common:
            raise ConfigError(f'{name}: Trying to override the names {common} from parent config {parent.value}')

        entries.update(items)

    return meta, entries
