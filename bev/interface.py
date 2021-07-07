import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence

from wcmatch import glob
from connectome.storage import Storage

from .config import CONFIG, build_storage, find_vcs_root
from .hash import is_hash, to_hash, from_hash, load_tree_hash, load_tree_key, strip_tree
from .local import Local
from .utils import InconsistentRepositories, call_git, HashNotFound, PathLike, RepositoryNotFound

# TODO: add `Local` here
Version = str


class Repository:
    def __init__(self, root: PathLike, storage: Storage, cache: PathLike = None):
        self.storage = storage
        self.root = Path(root)
        self.cache = cache

    @classmethod
    def from_root(cls, *parts: PathLike):
        root = Path(*parts)
        storage, cache = build_storage(root)
        return cls(root, storage, cache)

    @classmethod
    def from_vcs(cls, *parts: PathLike):
        vcs = find_vcs_root(Path(os.getcwd(), *parts))
        if vcs is None:
            raise RepositoryNotFound(f'{Path(*parts)} is not inside a vcs repository')

        configs = list(vcs.rglob(CONFIG))
        if not configs:
            raise RepositoryNotFound(f'{Path(*parts)} is not inside a vcs repository')
        if len(configs) > 1:
            raise InconsistentRepositories(f'This vcs repository contains multiple bev repositories: {configs}')

        return cls.from_root(configs[0].parent)

    @property
    def current_version(self):
        return self.latest_version()

    def latest_version(self, path: PathLike = '.'):
        path = Path(path)
        if not (self.root / path).exists() and not is_hash(path):
            path = to_hash(path)

        if not (self.root / path).exists():
            raise FileNotFoundError(path)

        return call_git(f'git log -n 1 --pretty=format:%H -- {path}', self.root)

    def resolve(self, *parts: PathLike, version: Version) -> Path:
        key = self.get_key(*parts, version=version)
        return self.storage.get_path(key)

    def glob(self, *parts: PathLike, version: Version) -> Sequence[Path]:
        key, hash_path, pattern = self._split(Path(*parts), self._get_hash, version)
        # TODO: add this to _split
        parent = from_hash(hash_path)

        assert pattern is not None
        pattern = str(pattern)
        tree = self.storage.load(load_tree_hash, key)

        files = set(tree)
        for file in tree:
            files.update(map(str, list(Path(file).parents)[:-1]))
        files = sorted(files)

        return [parent / file for file in glob.globfilter(files, pattern, flags=glob.GLOBSTAR)]

    # TODO: cache this based on path parents
    def get_key(self, *parts: PathLike, version: Version) -> str:
        key, _, inside = self._split(Path(*parts), self._get_hash, version)

        # `relative` is a hash by itself
        if inside is None:
            return key

        inside = str(inside)
        tree = self._get_tree(key, version)
        if inside not in tree:
            raise HashNotFound(inside)

        return tree[inside]

    def load_tree(self, path: PathLike, version: Version):
        exists, key = self._get_hash(Path(path), version)
        if not exists:
            raise HashNotFound(path)
        return self._get_tree(key, version)

    def _get_tree(self, key, version):
        if version == Local:
            return self.storage.load(load_tree_hash, key)
        return self._load_cached_tree(key)

    @lru_cache(None)
    def _load_cached_tree(self, key):
        return self.storage.load(load_tree_hash, key)

    def _get_hash(self, path: Path, version: Version):
        if version == Local:
            return self._get_uncomitted_hash(path)
        return self._get_committed_hash(path, version)

    def _get_uncomitted_hash(self, relative: Path):
        path = self.root / relative
        if not path.exists():
            return False, None

        return True, load_tree_key(path)

    @lru_cache(None)
    def _get_committed_hash(self, relative: Path, version: str):
        relative = str(relative)
        if not relative.startswith('./'):
            relative = f'./{relative}'

        try:
            # TODO: just return None or str?
            key = strip_tree(call_git(f'git show {version}:{relative}', self.root))
            return True, key
        except subprocess.CalledProcessError:
            return False, None

    @staticmethod
    def _split(path: Path, read: Callable, *args):
        # TODO: use bin-search?
        for parent in list(reversed(path.parents))[1:]:
            hash_path = to_hash(parent)
            exists, payload = read(hash_path, *args)
            if exists:
                # TODO: make sure it's a tree hash
                return payload, hash_path, path.relative_to(parent)

        hash_path = to_hash(path)
        exists, payload = read(hash_path, *args)
        if not exists:
            raise HashNotFound(path)

        # TODO: make sure it's not a tree hash
        return payload, hash_path, None
