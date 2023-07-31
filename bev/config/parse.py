import importlib
from pathlib import Path
from typing import Callable, NamedTuple, Optional, Sequence, Tuple, Type

from jboc import collect
from pydantic import ValidationError
from tarn import HashKeyStorage, Location, Writable
from tarn.compat import HashAlgorithm
from tarn.config import HashConfig
from yaml import safe_load

from ..exceptions import ConfigError
from .base import ConfigMeta, RepositoryConfig, StorageCluster
from .compat import model_copy, model_validate
from .legacy import LegacyStorageCluster
from .utils import CONFIG, choose_local, default_choose


class CacheStorageIndex(NamedTuple):
    local: Location
    remote: Sequence[Location]
    storage: HashKeyStorage
    algorithm: Optional[Type[HashAlgorithm]]


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
        algorithm=HashConfig(meta.hash).build() if isinstance(meta.hash, str) else meta.hash.build()
    )
    index = None
    if config.local.cache is not None:
        cache_storage = HashKeyStorage(
            config.local.cache.storage.local.build(),
            remote=filter_remotes([remote.cache.storage for remote in config.remotes if remote.cache is not None]),
            labels=meta.labels,
            algorithm=HashConfig(meta.hash.build()) if isinstance(meta.hash, str) else meta.hash.build()
        )
        index = CacheStorageIndex(
            GetItemPatch(config.local.cache.index.local.build()),
            filter_remotes([remote.cache.index for remote in config.remotes if remote.cache is not None]),
            cache_storage,
            algorithm=HashConfig(meta.hash).build() if isinstance(meta.hash, str) else meta.hash.build()
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
    # TODO: a lot of legacy code that will be removed after a few releases
    try:
        return StorageCluster(**entry)
    except ValidationError as e:
        exc = e
    try:
        cluster = LegacyStorageCluster(**entry)
    except ValidationError:
        pass
    else:
        kwargs = dict(name=cluster.name, hostname=cluster.hostname, storage=cluster.new_storage())
        cache = cluster.new_cache()
        if cache is not None:
            kwargs['cache'] = cache
        return StorageCluster(**kwargs)
    raise exc


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
            k: getattr(parent_meta, k) for k in ('fallback', 'order', 'choose', 'hash') if getattr(meta, k) is None
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


class GetItemPatch(Writable):
    def __init__(self, location):
        self.location = location
        self.locations = [location]

    def __getattr__(self, attr):
        return getattr(self.location, attr)

    def __getitem__(self, item):
        assert item == 0
        return self

    def read(self, *args, **kwargs):
        return self.location.read(*args, **kwargs)

    def read_batch(self, *args, **kwargs):
        return self.location.read_batch(*args, **kwargs)

    def write(self, *args, **kwargs):
        return self.location.write(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.location.delete(*args, **kwargs)

    def contents(self, *args, **kwargs):
        return self.location.contents(*args, **kwargs)
