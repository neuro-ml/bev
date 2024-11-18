import importlib
from pathlib import Path
from typing import Callable, NamedTuple, Sequence, Tuple

from jboc import collect
from tarn import HashKeyStorage, Location
from yaml import safe_load

from ..exceptions import ConfigError
from .base import ConfigMeta, RepositoryConfig, StorageCluster
from .compat import model_copy, model_validate
from .utils import CONFIG, choose_local, default_choose


class CacheStorageIndex(NamedTuple):
    local: Location
    remote: Sequence[Location]
    storage: HashKeyStorage


def load_config(config: Path) -> RepositoryConfig:
    with open(config, 'r') as file:
        return parse(Path(config), safe_load(file))


def build_storage(root: Path) -> Tuple[HashKeyStorage, CacheStorageIndex]:
    config = load_config(root / CONFIG)
    meta = config.meta

    storage = HashKeyStorage(
        config.local.storage.local.build(),
        remote=filter_remotes([remote.storage for remote in config.remotes]),
        labels=meta.labels,
        algorithm=None if meta.hash is None else meta.hash.build()
    )
    index = None
    if config.local.cache is not None:
        cache_storage = HashKeyStorage(
            config.local.cache.storage.local.build(),
            remote=filter_remotes([remote.cache.storage for remote in config.remotes if remote.cache is not None]),
            labels=meta.labels,
            algorithm=None if meta.hash is None else meta.hash.build()
        )
        index = CacheStorageIndex(
            config.local.cache.index.local.build(),
            filter_remotes([remote.cache.index for remote in config.remotes if remote.cache is not None]),
            cache_storage,
        )
    return storage, index


@collect
def filter_remotes(entries):
    for entry in entries:
        # TODO: add a test for a None remote
        if entry.remote is not None:
            entry = entry.remote.build()
            if entry is not None:
                yield entry


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


def _parse_entry(name, entry):
    if isinstance(entry, str):
        entry = {'storage': entry}
    if not isinstance(entry, dict):
        raise ConfigError(f'{name}: Each config entry must be either a dict or a string')
    if 'name' in entry:
        raise ConfigError(f'{name}: The key "name" is not available')
    entry = entry.copy()
    entry['name'] = name
    return StorageCluster(**entry)


def _parse(name, config, root):
    if not isinstance(config, dict):
        raise ConfigError(f'{name}: The config must be a dict')

    config = config.copy()
    meta = model_validate(ConfigMeta, config.pop('meta', {}))
    # parse own items
    entries = {}
    for name, entry in config.items():
        entries[name] = _parse_entry(name, entry)

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
            k: getattr(parent_meta, k) for k in ('fallback', 'choose', 'hash') if getattr(meta, k) is None
        })
        if meta.hash is None:
            meta = model_copy(meta, update=dict(hash=parent_meta.hash))
        elif parent_meta.hash is not None and meta.hash != parent_meta.hash:
            raise ConfigError(
                f'{name}: The parent config ({parent.value}) has a different hash spec: '
                f'{meta.hash} vs {parent_meta.hash}'
            )

        entries.update(items)

    meta = model_copy(meta, update=override)
    return meta, entries
