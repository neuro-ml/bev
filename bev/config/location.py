import os
import warnings
from pathlib import Path
from typing import Optional, Sequence, Union

import humanfriendly
import yaml
from jboc import collect
from paramiko.config import SSHConfig
from pytimeparse.timeparse import timeparse
from tarn import S3, SCP, SFTP, DiskDict, Fanout, Level, Levels, Location, Nginx, RedisLocation, SmallLocation
from tarn.config import CONFIG_NAME as STORAGE_CONFIG_NAME, StorageConfig as TarnStorageConfig
from tarn.utils import mkdir

from .compat import NoExtra, core_schema, field_validator, model_dump, model_validate
from .registry import RegistryError, add_type, find, register


@add_type
class LocationConfig(NoExtra):
    @classmethod
    def __get_validators__(cls):
        yield lambda v: from_special(v)
        yield from super().__get_validators__()

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return core_schema.no_info_before_validator_function(
            lambda v: from_special(v) if cls is LocationConfig else v,
            _handler(_source_type),
        )

    @classmethod
    def from_special(cls, v):
        """ Parse an object different from a dict """

    def build(self) -> Optional[Location]:
        """ Build a live object from its config """
        raise NotImplementedError

    def init(self, meta, permissions, group):
        """ Initialize the location if possible """


@register('diskdict')
class DiskDictConfig(LocationConfig):
    root: Path

    @classmethod
    def from_special(cls, v):
        if isinstance(v, str):
            return cls(root=v)

    def build(self) -> Optional[Location]:
        if self.root.exists():
            return DiskDict(self.root)

    def init(self, meta, permissions, group):
        if not self.root.exists():
            mkdir(self.root, permissions, group, parents=True)
            conf_path = self.root / STORAGE_CONFIG_NAME
            if not conf_path.exists():
                with open(conf_path, 'w') as file:
                    yaml.safe_dump(model_dump(TarnStorageConfig(hash=meta.hash), exclude_defaults=True), file)


@register('fanout')
class FanoutConfig(LocationConfig):
    locations: Sequence[LocationConfig]

    @classmethod
    def from_special(cls, v):
        if isinstance(v, (list, tuple)):
            return cls(locations=v)

    def build(self) -> Location:
        locations = list(filter(None, (location.build() for location in self.locations)))
        if locations:
            return Fanout(*locations)

    def init(self, meta, permissions, group):
        for location in self.locations:
            location.init(meta, permissions, group)


class LevelConfig(NoExtra):
    location: LocationConfig
    write: bool = True
    replicate: bool = True
    touch: bool = False


@register('levels')
class LevelsConfig(LocationConfig):
    levels: Sequence[LevelConfig]

    # TODO: https://docs.pydantic.dev/latest/usage/validators/#generic-validated-collections
    @field_validator('levels', mode='before')
    @collect
    def _from_location(cls, vs):
        for v in vs:
            if (
                    (isinstance(v, dict) and set(v) <= {'location', 'write', 'replicate', 'touch'}) or
                    isinstance(v, LevelConfig)
            ):
                yield v
            else:
                yield {'location': v}

    @classmethod
    def from_special(cls, v):
        if isinstance(v, (list, tuple)):
            return cls(levels=v)

    def build(self) -> Location:
        levels = []
        for level in self.levels:
            loc = level.location.build()
            if loc is not None:
                levels.append(Level(loc, level.write, level.replicate, level.touch))

        if levels:
            return Levels(*levels)

    def init(self, meta, permissions, group):
        for level in self.levels:
            level.location.init(meta, permissions, group)


class SSHRemoteConfig(LocationConfig):
    host: str
    root: Path
    _location: Optional[type] = None

    @classmethod
    def from_special(cls, v):
        # TODO: properly parse ssh link
        if isinstance(v, str):
            if ':' not in v:
                warnings.warn(
                    'Please provide a path alongside the host in the format "host:path". '
                    'This will raise an error in the future.', UserWarning
                )
                host, root = v, ''
            else:
                host, root = v.split(':', 1)
            return cls(host=host, root=root)

    def build(self) -> Optional[Location]:
        if self._location is None:
            return None
        config_path = Path('~/.ssh/config').expanduser()
        if config_path.exists():
            with open(config_path) as f:
                ssh_config = SSHConfig()
                ssh_config.parse(f)

            # TODO: better way of handling missing hosts
            if ssh_config.lookup(self.host) != {'hostname': self.host} or self.host in ssh_config.get_hostnames():
                return self._location(self.host, self.root)


@register('nginx')
class NginxConfig(LocationConfig):
    url: str

    @classmethod
    def from_special(cls, v):
        if isinstance(v, str):
            return cls(url=v)

    def build(self) -> Optional[Location]:
        return Nginx(self.url)


def from_special(x, passthrough: bool = True):
    if isinstance(x, str):
        return DiskDictConfig(root=x)
    if isinstance(x, (list, tuple)):
        return FanoutConfig(locations=x)
    if isinstance(x, dict) and len(x) == 1:
        (name, args), = x.items()
        if isinstance(name, str):
            try:
                cls = find(name, LocationConfig)
            except RegistryError:
                pass

            else:
                if not isinstance(args, dict):
                    result = cls.from_special(args)
                    if result is None:
                        raise ValueError(f'Unsupported type {type(args).__name__!r}')
                    return result
                return model_validate(cls, args)

    if passthrough:
        return x


@register('s3')
class S3Config(LocationConfig):
    url: str
    bucket: str
    credentials_file: Optional[str] = None

    def build(self) -> Optional[Location]:
        # we carefully patch the os.environ here
        # FIXME: this is not thread safe though
        if self.credentials_file is not None:
            path = Path(self.credentials_file).expanduser()
            name = 'AWS_SHARED_CREDENTIALS_FILE'

            current_path = os.environ.get(name)
            if current_path and Path(current_path).expanduser() != path:
                raise ValueError(
                    'Cannot overwrite the current value in "AWS_SHARED_CREDENTIALS_FILE": '
                    f'{current_path} vs {path}'
                )

            os.environ[name] = str(path)

        return S3(self.url, self.bucket)


@register('redis')
class RedisConfig(LocationConfig):
    url: str
    prefix: str = '_'
    keep_labels: bool = False
    keep_usage: bool = False
    ttl: Optional[Union[int, str]] = None

    @classmethod
    def from_special(cls, v):
        if isinstance(v, str):
            return cls(url=v)

    def build(self) -> Optional[Location]:
        if isinstance(self.ttl, str):
            ttl = timeparse(self.ttl)
            if ttl is None:
                raise ValueError(f'The time format could not be parsed: {self.ttl}')
        else:
            ttl = self.ttl
        return RedisLocation(self.url, prefix=self.prefix, keep_labels=self.keep_labels,
                             keep_usage=self.keep_usage, ttl=ttl)


@register('small')
class SmallConfig(LocationConfig):
    location: LocationConfig
    max_size: int

    @field_validator('max_size', mode='before')
    def _from_str(cls, v):
        if isinstance(v, str):
            return humanfriendly.parse_size(v)
        return v

    def build(self) -> Location:
        return SmallLocation(self.location.build(), self.max_size)


@register('scp')
class SCPConfig(SSHRemoteConfig):
    _location = SCP


@register('sftp')
class SFTPConfig(SSHRemoteConfig):
    _location = SFTP
