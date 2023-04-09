from pathlib import Path
from typing import Union

from paramiko.config import SSHConfig
from pydantic import BaseModel, Extra
from tarn import SCP, Location, Nginx

from .registry import add_type, register


class NoExtra(BaseModel):
    class Config:
        extra = Extra.forbid


@add_type
class RemoteConfig(NoExtra):
    @classmethod
    def from_string(cls, v):
        raise NotImplementedError

    def build(self, root: Union[Path, None], optional: bool) -> Union[Location, None]:
        raise NotImplementedError


@register('scp')
class SCPRemote(RemoteConfig):
    host: str

    @classmethod
    def from_string(cls, v):
        return cls(host=v)

    def build(self, root: Union[Path, None], optional: bool) -> Union[Location, None]:
        config_path = Path('~/.ssh/config').expanduser()
        if config_path.exists():
            with open(config_path) as f:
                ssh_config = SSHConfig()
                ssh_config.parse(f)

            # TODO: better way of handling missing hosts
            if ssh_config.lookup(self.host) != {'hostname': self.host} or self.host in ssh_config.get_hostnames():
                return SCP(self.host, root)


@register('nginx')
class NginxRemote(RemoteConfig):
    url: str

    @classmethod
    def from_string(cls, v):
        return cls(url=v)

    def build(self, root: Union[Path, None], optional: bool) -> Union[Location, None]:
        return Nginx(self.url)


# TODO: legacy
register('ssh', SCPRemote)
register('http', NginxRemote)
