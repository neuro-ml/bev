import yaml
from paramiko.config import SSHConfig
from pathlib import Path
from pydantic import BaseModel, Extra
from pydantic import validator
from typing import Sequence, Optional

from tarn import SCP, Location, Nginx, DiskDict, Fanout, Levels, Level
from tarn.utils import mkdir
from tarn.config import CONFIG_NAME as STORAGE_CONFIG_NAME, StorageConfig as TarnStorageConfig

from .registry import add_type, register, find


class NoExtra(BaseModel):
    class Config:
        extra = Extra.forbid


@add_type
class LocationConfig(NoExtra):
    @classmethod
    def __get_validators__(cls):
        yield lambda v: from_special(v)
        yield from super().__get_validators__()

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
                    yaml.safe_dump(TarnStorageConfig(hash=meta.hash).dict(exclude_defaults=True), file)


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


@register('levels')
class LevelsConfig(LocationConfig):
    levels: Sequence[LevelConfig]

    @validator('levels', pre=True, each_item=True)
    def _from_location(cls, v):
        if (isinstance(v, dict) and set(v) <= {'location', 'write', 'replicate'}) or isinstance(v, LevelConfig):
            return v
        return {'location': v}

    @classmethod
    def from_special(cls, v):
        if isinstance(v, (list, tuple)):
            return cls(levels=v)

    def build(self) -> Location:
        levels = []
        for level in self.levels:
            loc = level.location.build()
            if loc is not None:
                levels.append(Level(loc, level.write, level.replicate))

        if levels:
            return Levels(*levels)

    def init(self, meta, permissions, group):
        for level in self.levels:
            level.location.init(meta, permissions, group)


@register('scp')
class SCPConfig(LocationConfig):
    host: str
    root: Path

    @classmethod
    def from_special(cls, v):
        # TODO: properly parse ssh link
        if isinstance(v, str):
            host, root = v.split(':', 1)
            return cls(host=host, root=root)

    def build(self) -> Optional[Location]:
        config_path = Path('~/.ssh/config').expanduser()
        if config_path.exists():
            with open(config_path) as f:
                ssh_config = SSHConfig()
                ssh_config.parse(f)

            # TODO: better way of handling missing hosts
            if ssh_config.lookup(self.host) != {'hostname': self.host} or self.host in ssh_config.get_hostnames():
                return SCP(self.host, self.root)


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
                cls = find(LocationConfig, name)
            except ValueError:
                pass

            else:
                if not isinstance(args, dict):
                    result = cls.from_special(args)
                    if result is None:
                        raise ValueError(f'Unsupported type {type(args).__name__!r}')
                    return result
                return cls.parse_obj(args)

    if passthrough:
        return x