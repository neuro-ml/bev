import os
import socket
from itertools import chain
from pathlib import Path

from tarn import StorageLevel

from .base import StorageCluster
from .hostname import StrHostName
from ..exceptions import ConfigError
from ..utils import PathOrStr

CONFIG = '.bev.yml'


def identity(x):
    return x


def wrap_levels(levels, cls, order=identity, **kwargs):
    return tuple(
        StorageLevel(
            order([cls(location.root, **kwargs) for location in level.locations]),
            write=level.write, replicate=level.replicate, name=level.name,
        )
        for level in _filter_levels(levels)
    )


def _filter_levels(levels):
    for level in levels:
        locations = [
            x for x in level.locations
            if not x.optional or x.root.exists()
        ]
        if locations:
            level = level.copy()
            level.locations = locations
            yield level


def choose_local(metas, func, default, root):
    for meta in metas.values():
        if func(meta):
            return meta.name

    if default is not None and default not in metas:
        raise ConfigError(f'The fallback ({default}) is not present in the config {root}')

    return default


def default_choose(meta: StorageCluster):
    repo_key = 'BEV__REPOSITORY'
    if repo_key in os.environ:
        return meta.name == os.environ[repo_key]

    node = socket.gethostname()
    hosts = meta.hostname or [StrHostName(meta.name)]
    return any(h.match(node) for h in hosts)


def _find_root(path: PathOrStr, marker: str) -> Path:
    path = Path(path).resolve()
    for parent in chain([path], path.parents):
        if (parent / marker).exists():
            return parent


def find_repo_root(path: PathOrStr) -> Path:
    return _find_root(path, CONFIG)


def find_vcs_root(path: PathOrStr) -> Path:
    return _find_root(path, '.git')
