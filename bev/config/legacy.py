from pathlib import Path

from jboc import collect
from pydantic import ValidationError
from typing import Any, Dict, Optional, Sequence

from .base import StorageConfig
from .compat import model_validator, field_validator
from .hostname import HostName
from .location import LocationConfig, NoExtra
from .registry import RegistryError, find


class LegacyLocationConfig(NoExtra):
    root: Path = None
    remote: Sequence[LocationConfig] = ()
    optional: bool = False

    @model_validator(mode='before')
    def from_string(cls, v):
        if isinstance(v, str):
            return cls(root=v)
        return v

    @model_validator(mode='before')
    def gather_remote(cls, values):
        if isinstance(values, StorageLevelConfig):
            return values
        values = to_values(values).copy()
        remote = list(values.pop('remote', []))
        for key in list(values):
            if key not in ['root', 'optional']:
                remote.append({key: values.pop(key)})

        values['remote'] = tuple(remote)
        return values

    @field_validator('remote', mode='before')
    def from_single(cls, v):
        if isinstance(v, (str, dict, LocationConfig)):
            v = v,

        return list(map(cls.parse_entry, v))

    @staticmethod
    def parse_entry(entry):
        if isinstance(entry, LocationConfig):
            return entry

        assert isinstance(entry, dict), f'Not a dict: {entry}'
        assert len(entry) == 1, entry
        (k, entry), = entry.items()
        if isinstance(entry, LocationConfig):
            return entry

        try:
            kls = find(k, LocationConfig)
        except RegistryError as e:
            raise ValueError(str(e)) from e
        if isinstance(entry, str):
            return kls.from_special(entry)
        return kls.parse_obj(entry)


class StorageLevelConfig(NoExtra):
    default: Dict[str, Any] = None
    locations: Sequence[LegacyLocationConfig]
    write: bool = True
    replicate: bool = True
    name: Optional[str] = None

    @model_validator(mode='before')
    def from_builtins(cls, v):
        if isinstance(v, dict):
            return v
        return cls(locations=v)

    @field_validator('default', mode='before', always=True)
    def fill(cls, v):
        if v is None:
            return {}
        return v

    @field_validator('locations', mode='before')
    @collect
    def add_defaults(cls, vs, values):
        if not isinstance(vs, (list, tuple)):
            vs = vs,
        values = to_values(values)
        for v in vs:
            default = (values['default'] or {}).copy()
            if isinstance(v, str):
                v = {'root': v}

            if default:
                assert isinstance(v, dict), type(v)
                default.update(v)
                yield default

            else:
                yield v

    @field_validator('locations')
    def to_tuple(cls, v):
        return tuple(v)


class LegacyCacheConfig(NoExtra):
    index: Sequence[StorageLevelConfig]
    storage: Sequence[StorageLevelConfig]
    default: Dict[str, Any] = None


class LegacyStorageCluster(NoExtra):
    name: str
    default: Dict[str, Any] = None
    hostname: Sequence[HostName] = ()
    storage: Sequence[StorageLevelConfig]
    cache: LegacyCacheConfig = None

    def _new(self, old):
        levels = []
        for level in old:
            fanout = []
            for entry in level.locations:
                if entry.root is not None:
                    fanout.append({'diskdict': str(entry.root)})

            if fanout:
                if len(fanout) == 1:
                    levels.append(fanout[0])
                else:
                    levels.append({'fanout': fanout})

        if len(levels) > 1:
            local = {'levels': levels}
        else:
            local = levels[0]
        return StorageConfig(local=local)

    def new_storage(self):
        return self._new(self.storage)

    def new_cache(self):
        if self.cache is not None:
            index = self._new(self.cache.index)
            print(self.cache, self.cache.index, index, self._new(self.cache.storage))
            if index is not None:
                return {'index': index, 'storage': self._new(self.cache.storage)}

    @field_validator('hostname', mode='before')
    def from_single(cls, v):
        if isinstance(v, (str, dict, HostName)):
            v = v,
        return v

    @field_validator('storage', mode='before')
    def validate_storage(cls, v, values):
        values = to_values(values)
        default = (values['default'] or {}).copy()
        return cls._parse_storage_levels(v, default)

    @field_validator('cache', mode='before')
    def validate_cache(cls, v, values):
        values = to_values(values)
        default = (values['default'] or {}).copy()

        if isinstance(v, dict) and 'index' in v:
            v = v.copy()
            default.update(v.pop('default', {}))
            if 'storage' not in values:
                raise ValueError('No valid storage config found')
            storage = cls._parse_storage_levels(v.pop('storage', values['storage']), default)
            index = cls._parse_storage_levels(v.pop('index'), default)
            return LegacyCacheConfig(**v, index=index, default=default, storage=storage)

        index = cls._parse_storage_levels(v, default)
        if 'storage' not in values:
            raise ValueError('No valid storage config found')
        storage = cls._parse_storage_levels(values['storage'], default)
        return LegacyCacheConfig(index=index, storage=storage, default=default)

    @staticmethod
    def _parse_storage_levels(v, default):
        if isinstance(v, (str, dict, StorageLevelConfig, LegacyLocationConfig)):
            v = v,

        # first try to interpret the entire storage as a single level
        try:
            return StorageLevelConfig(locations=v, default=default),
        except ValidationError:
            pass

        result = []
        for entry in v:
            if isinstance(v, StorageLevelConfig):
                result.append(v)
            elif isinstance(entry, (str, LegacyLocationConfig)):
                entry = StorageLevelConfig(locations=entry, default=default)
            elif isinstance(entry, dict):
                local_entry = entry.copy()
                local_default = local_entry.pop('default', {}).copy()
                local_default.update(default)
                local_entry['default'] = local_default

                if set(local_entry) <= {'locations', 'default', 'write', 'replicate', 'name'}:
                    entry = StorageLevelConfig(**local_entry)
                else:
                    entry = StorageLevelConfig(locations=entry, default=default)

            result.append(entry)

        return tuple(result)


def to_values(x):
    return x if isinstance(x, dict) else x.data
