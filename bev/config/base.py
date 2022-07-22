from pathlib import Path
from typing import Dict, Sequence, Any, Union, Optional

from pydantic import validator, root_validator, ValidationError
from tarn.config import HashConfig

from .hostname import HostName
from .include import Include
from .remote import RemoteConfig, NoExtra
from .registry import find


class LocationConfig(NoExtra):
    root: Path = None
    remote: Sequence[RemoteConfig] = ()
    optional: bool = False

    @root_validator(pre=True)
    def from_string(cls, v):
        if isinstance(v, str):
            return cls(root=v)
        return v

    @root_validator(pre=True)
    def gather_remote(cls, values):
        values = values.copy()
        remote = list(values.pop('remote', []))
        for key in list(values):
            if key not in ['root', 'optional']:
                remote.append({key: values.pop(key)})

        values['remote'] = tuple(remote)
        return values

    @validator('remote', pre=True)
    def from_single(cls, v):
        if isinstance(v, (str, dict, RemoteConfig)):
            v = v,

        return list(map(cls.parse_entry, v))

    @staticmethod
    def parse_entry(entry):
        if isinstance(entry, RemoteConfig):
            return entry

        assert isinstance(entry, dict), f'Not a dict: {entry}'
        assert len(entry) == 1, entry
        (k, entry), = entry.items()
        if isinstance(entry, RemoteConfig):
            return entry

        kls = find(RemoteConfig, k)
        if isinstance(entry, str):
            return kls.from_string(entry)
        return kls.parse_obj(entry)


class StorageLevelConfig(NoExtra):
    default: Dict[str, Any] = None
    locations: Sequence[LocationConfig]
    write: bool = True
    replicate: bool = True
    name: Optional[str] = None

    @root_validator(pre=True)
    def from_builtins(cls, v):
        if isinstance(v, dict):
            return v
        return cls(locations=v)

    @validator('default', pre=True, always=True)
    def fill(cls, v):
        if v is None:
            return {}
        return v

    @validator('locations', pre=True)
    def from_string(cls, v):
        if isinstance(v, str):
            v = v,
        return v

    @validator('locations', each_item=True, pre=True)
    def add_defaults(cls, v, values):
        default = (values['default'] or {}).copy()
        if isinstance(v, str):
            v = {'root': v}

        if default:
            assert isinstance(v, dict), type(v)
            default.update(v)
            return default

        return v

    @validator('locations')
    def to_tuple(cls, v):
        return tuple(v)


class StorageCluster(NoExtra):
    name: str
    default: Dict[str, Any] = None
    hostname: Sequence[HostName] = ()
    storage: Sequence[StorageLevelConfig]
    cache: Sequence[StorageLevelConfig] = ()

    @validator('hostname', pre=True)
    def from_single(cls, v):
        if isinstance(v, (str, dict, HostName)):
            v = v,
        return v

    @validator('storage', 'cache', pre=True)
    def from_string(cls, v, values):
        if isinstance(v, (str, dict, StorageLevelConfig, LocationConfig)):
            v = v,

        default = (values['default'] or {}).copy()
        # first try to interpret the entire storage as a single level
        try:
            return StorageLevelConfig(locations=v, default=default),
        except ValidationError:
            pass

        result = []
        for entry in v:
            if isinstance(entry, (str, LocationConfig)):
                entry = StorageLevelConfig(locations=entry, default=default)
            elif isinstance(entry, dict):
                local_entry = entry.copy()
                local_default = local_entry.pop('default', {}).copy()
                local_default.update(default)
                local_entry['default'] = local_default

                try:
                    entry = StorageLevelConfig(**local_entry)
                except ValidationError:
                    entry = StorageLevelConfig(locations=entry, default=default)

            result.append(entry)

        return tuple(result)


class ConfigMeta(NoExtra):
    choose: str = None
    fallback: str = None
    order: str = None
    hash: Union[str, HashConfig] = None
    include: Sequence[Include] = ()

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
