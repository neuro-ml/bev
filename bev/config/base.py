from typing import Any, Dict, Optional, Sequence

from tarn.config import HashConfig

from .compat import field_validator, model_validator
from .hostname import HostName
from .include import Include
from .location import LocationConfig, NoExtra, from_special


class StorageConfig(NoExtra):
    local: Optional[LocationConfig] = None
    remote: Optional[LocationConfig] = None

    @model_validator(mode='before')
    def locations(cls, values):
        assert values, 'at least one entry must be provided'
        if not set(values) <= {'local', 'remote'}:
            values = {'local': values}
        return {k: from_special(v) for k, v in values.items()}


class CacheConfig(NoExtra):
    index: StorageConfig
    storage: StorageConfig

    @field_validator('index', 'storage', mode='before')
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

    @field_validator('hostname', mode='before')
    def from_single(cls, v):
        if isinstance(v, (str, dict, HostName)):
            v = v,
        return v

    @field_validator('storage', mode='before')
    def validate_storage(cls, v):
        res = from_special(v, False)
        if res is not None:
            return StorageConfig(local=res)
        return v

    @field_validator('cache', mode='before')
    def validate_cache(cls, v, values):
        if isinstance(v, CacheConfig):
            return v
        if not (isinstance(v, dict) and set(v) <= {'index', 'storage'}):
            v = {'index': v}

        if 'storage' not in v:
            # FIXME
            if not isinstance(values, dict):
                values = values.data
            if 'storage' not in values:
                raise ValueError('No valid `storage` configuration found')
            v = v.copy()
            v['storage'] = values['storage']

        return v


class ConfigMeta(NoExtra):
    choose: str = None
    fallback: str = None
    hash: Optional[HashConfig] = None
    include: Sequence[Include] = ()
    labels: Optional[Sequence[str]] = None

    @field_validator('hash', mode='before')
    def normalize_hash(cls, v):
        if isinstance(v, str):
            v = {'name': v}
        return v

    @field_validator('include', mode='before')
    def from_single(cls, v):
        if isinstance(v, (dict, Include)):
            v = v,
        return v


class RepositoryConfig(NoExtra):
    local: StorageCluster
    remotes: Sequence[StorageCluster]
    meta: ConfigMeta
