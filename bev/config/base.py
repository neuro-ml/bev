from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union

from pydantic import ValidationError, root_validator, validator
from tarn.config import HashConfig

from .hostname import HostName
from .include import Include
from .location import NoExtra, LocationConfig, from_special


# from .remote import NoExtra, RemoteConfig
#
#
# class LocationConfig(NoExtra):
#     root: Path = None
#     remote: Sequence[RemoteConfig] = ()
#     optional: bool = False
#
#     @root_validator(pre=True)
#     def from_string(cls, v):
#         if isinstance(v, str):
#             return cls(root=v)
#         return v
#
#     @root_validator(pre=True)
#     def gather_remote(cls, values):
#         values = values.copy()
#         remote = list(values.pop('remote', []))
#         for key in list(values):
#             if key not in ['root', 'optional']:
#                 remote.append({key: values.pop(key)})
#
#         values['remote'] = tuple(remote)
#         return values
#
#     @validator('remote', pre=True)
#     def from_single(cls, v):
#         if isinstance(v, (str, dict, RemoteConfig)):
#             v = v,
#
#         return list(map(cls.parse_entry, v))
#
#     @staticmethod
#     def parse_entry(entry):
#         if isinstance(entry, RemoteConfig):
#             return entry
#
#         assert isinstance(entry, dict), f'Not a dict: {entry}'
#         assert len(entry) == 1, entry
#         (k, entry), = entry.items()
#         if isinstance(entry, RemoteConfig):
#             return entry
#
#         kls = find(RemoteConfig, k)
#         if isinstance(entry, str):
#             return kls.from_string(entry)
#         return kls.parse_obj(entry)
#
#
# class StorageLevelConfig(NoExtra):
#     default: Dict[str, Any] = None
#     locations: Sequence[LocationConfig]
#     write: bool = True
#     replicate: bool = True
#     name: Optional[str] = None
#
#     @root_validator(pre=True)
#     def from_builtins(cls, v):
#         if isinstance(v, dict):
#             return v
#         return cls(locations=v)
#
#     @validator('default', pre=True, always=True)
#     def fill(cls, v):
#         if v is None:
#             return {}
#         return v
#
#     @validator('locations', pre=True)
#     def from_string(cls, v):
#         if isinstance(v, str):
#             v = v,
#         return v
#
#     @validator('locations', each_item=True, pre=True)
#     def add_defaults(cls, v, values):
#         default = (values['default'] or {}).copy()
#         if isinstance(v, str):
#             v = {'root': v}
#
#         if default:
#             assert isinstance(v, dict), type(v)
#             default.update(v)
#             return default
#
#         return v
#
#     @validator('locations')
#     def to_tuple(cls, v):
#         return tuple(v)


class StorageConfig(NoExtra):
    local: LocationConfig
    remote: Optional[LocationConfig] = None

    @root_validator(pre=True)
    def locations(cls, values):
        if not set(values) <= {'local', 'remote'}:
            return {'local': values}
        return values


class CacheConfig(NoExtra):
    index: StorageConfig
    storage: StorageConfig

    @validator('index', 'storage', pre=True)
    def validate_storage(cls, v):
        res = from_special(v, False)
        if res is not None:
            return StorageConfig(local=res)
        return v


class StorageCluster(NoExtra):
    name: str
    default: Dict[str, Any] = None
    hostname: Sequence[HostName] = ()
    storage: StorageConfig
    cache: CacheConfig = None

    @validator('hostname', pre=True)
    def from_single(cls, v):
        if isinstance(v, (str, dict, HostName)):
            v = v,
        return v

    @validator('storage', pre=True)
    def validate_storage(cls, v):
        res = from_special(v, False)
        if res is not None:
            return StorageConfig(local=res)
        return v

    @validator('cache', pre=True)
    def validate_cache(cls, v, values):
        if isinstance(v, CacheConfig):
            return v
        if not (isinstance(v, dict) and set(v) <= {'index', 'storage'}):
            v = {'index': v}

        if 'storage' not in v:
            if 'storage' not in values:
                raise ValueError('No valid `storage` configuration found')
            v = v.copy()
            v['storage'] = values['storage']

        return v


class ConfigMeta(NoExtra):
    choose: str = None
    fallback: str = None
    order: str = None
    hash: Union[str, HashConfig] = None
    include: Sequence[Include] = ()
    labels: Optional[Sequence[str]] = None

    _override = 'fallback', 'order', 'choose', 'hash'

    @validator('hash', pre=True)
    def normalize_hash(cls, v):
        if isinstance(v, str):
            v = {'name': v}
        return v

    @validator('include', pre=True)
    def from_single(cls, v):
        if isinstance(v, (dict, Include)):
            v = v,
        return v


class RepositoryConfig(NoExtra):
    local: StorageCluster
    remotes: Sequence[StorageCluster]
    meta: ConfigMeta
