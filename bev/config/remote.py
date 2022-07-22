from pathlib import Path
from typing import Union

from paramiko.config import SSHConfig
from pydantic import BaseModel, Extra
from tarn import SSHLocation, RemoteStorage, HTTPLocation

from .registry import register, add_type


class NoExtra(BaseModel):
    class Config:
        extra = Extra.forbid


@add_type
class RemoteConfig(NoExtra):
    @classmethod
    def from_string(cls, v):
        raise NotImplementedError

    def build(self, root: Union[Path, None], optional: bool) -> Union[RemoteStorage, None]:
        raise NotImplementedError


@register('ssh')
class SHHRemote(RemoteConfig):
    host: str

    @classmethod
    def from_string(cls, v):
        return cls(host=v)

    def build(self, root: Union[Path, None], optional: bool) -> Union[RemoteStorage, None]:
        config_path = Path('~/.ssh/config').expanduser()
        if config_path.exists():
            with open(config_path) as f:
                ssh_config = SSHConfig()
                ssh_config.parse(f)

            # TODO: better way of handling missing hosts
            if ssh_config.lookup(self.host) != {'hostname': self.host} or self.host in ssh_config.get_hostnames():
                return SSHLocation(self.host, root, optional=optional)


@register('http')
class HTTPRemote(RemoteConfig):
    url: str

    @classmethod
    def from_string(cls, v):
        return cls(url=v)

    def build(self, root: Union[Path, None], optional: bool) -> Union[RemoteStorage, None]:
        return HTTPLocation(self.url, optional)
