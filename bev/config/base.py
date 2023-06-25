import warnings
from typing import Any, Dict, Optional, Sequence, Union

from pydantic import root_validator, validator
from tarn.config import HashConfig

from .hostname import HostName
from .include import Include
from .location import LocationConfig, NoExtra, from_special


class StorageConfig(NoExtra):
    local: Optional[LocationConfig] = None
    remote: Optional[LocationConfig] = None

    @root_validator(pre=True)
    def locations(cls, values):
        assert values, 'at least one entry must be provided'
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
    cache: Optional[CacheConfig] = None

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

    @validator('order')
    def deprecate_order(cls, v):
        if v is not None:
            warnings.warn('The field "order" is deprecated and has no effect anymore')

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
