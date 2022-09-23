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
    remote: Sequence[RemoteStorage]
    storage: Storage


def load_config(config: Path) -> RepositoryConfig:
    with open(config, 'r') as file:
        return parse(Path(config), safe_load(file))


def build_storage(root: Path) -> Tuple[Storage, CacheStorageIndex]:
    config = load_config(root / CONFIG)
    meta = config.meta

    order_func: Callable[[Sequence[Disk]], Sequence[Disk]] = identity
    if meta.order is not None:
        path, attr = meta.order.rsplit('.', 1)
        order_func = getattr(importlib.import_module(path), attr)

    storage = Storage(
        *wrap_levels(config.local.storage, Disk, order_func),
        remote=filter_remotes([remote.storage for remote in config.remotes])
    )
    index = None
    if config.local.cache is not None:
        cache_storage = Storage(
            *wrap_levels(config.local.cache.storage, Disk, order_func),
            remote=filter_remotes([remote.cache.storage for remote in config.remotes if remote.cache is not None])
        )
        index = CacheStorageIndex(
            tuple(_filter_levels(config.local.cache.index)),
            filter_remotes([remote.cache.index for remote in config.remotes if remote.cache is not None]),
            cache_storage,
        )
    return storage, index


def filter_remotes(entries):
    remotes = []
    for entry in entries:
        for level in entry:
            for location in level.locations:
                for remote in location.remote:
                    remote = remote.build(location.root, location.optional)
                    if remote is not None:
                        remotes.append(remote)

    return remotes


def parse(root, config) -> RepositoryConfig:
    meta, entries = _parse(root, config, root)

    filter_func: Callable[[StorageCluster], bool] = default_choose
    if meta.choose is not None:
        path, attr = meta.choose.rsplit('.', 1)
        filter_func = getattr(importlib.import_module(path), attr)

    if len(entries) == 1:
        local, = entries.values()
        remotes = ()
    else:
        name = choose_local(entries, filter_func, meta.fallback, root)
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
    override = {}
    for parent in meta.include:
        parent_root, parent_config = parent.read(root)
        if parent_config is None:
            if parent.optional:
                continue
            raise ConfigError(f'Parent config "{parent.value}" not found')

        parent_meta, items = _parse(parent.value, parent_config, parent_root)
        common = set(items) & set(entries)
        if common:
            raise ConfigError(f'{name}: Trying to override the names {common} from parent config {parent.value}')

        override.update({
            k: getattr(parent_meta, k) for k in ConfigMeta._override if getattr(meta, k) is None
        })
        if meta.hash is None:
            meta = meta.copy(update=dict(hash=parent_meta.hash))
        elif parent_meta.hash is not None and meta.hash != parent_meta.hash:
            raise ConfigError(
                f'{name}: The parent config ({parent.value}) has a different hash spec: '
                f'{meta.hash} vs {parent_meta.hash}'
            )

        entries.update(items)

    meta = meta.copy(update=override)
    return meta, entries
