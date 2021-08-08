import inspect
import os
import subprocess
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Sequence, Union

from wcmatch import glob

from .config import CONFIG, build_storage, find_vcs_root
from .hash import is_hash, to_hash, load_tree, load_tree_key, strip_tree, FileHash, TreeHash, Key
from .local import Local, LocalVersion
from .utils import InconsistentRepositories, call_git, HashNotFound, PathLike, RepositoryNotFound

CommittedVersion = str
Version = Union[CommittedVersion, LocalVersion]


class Repository:
    """
    Interface that represents a `bev` repository.

    Parameters
    ----------
    root:
        the path to the repository's root, i.e. the folder that contains `.bev.config`
    fetch: bool
        whether to fetch files from remote locations when needed. Can be overridden in corresponding methods
    version: str, Local
        default value for data version. Can be either a string with a commit hash/tag or the `Local` object.
        Can be overridden in corresponding methods
    """

    def __init__(self, *root: PathLike, fetch: bool = True, version: Version = None):
        self.root = Path(*root)
        self.storage, self.cache = build_storage(self.root)
        self._fetch, self._version = fetch, version

    @classmethod
    def from_root(cls, *parts: PathLike):
        warnings.warn(
            'This classmethod is deprecated, call the constructor directly for the same behaviour', UserWarning)
        return cls(*parts)

    @classmethod
    def from_here(cls, *relative: PathLike, fetch: bool = True, version: Version = None) -> 'Repository':
        """
        Creates a repository with a path `relative` to the file in which this method is called.

        Examples
        --------
        >>> repo = Repository.from_here('../../data')
        """
        file = Path(inspect.stack()[1].filename)
        return cls(file.parent / Path(*relative), fetch=fetch, version=version)

    @classmethod
    def from_vcs(cls, *parts: PathLike) -> 'Repository':
        vcs = find_vcs_root(Path(os.getcwd(), *parts))
        if vcs is None:
            raise RepositoryNotFound(f'{Path(*parts)} is not inside a vcs repository')

        configs = list(vcs.rglob(CONFIG))
        if not configs:
            raise RepositoryNotFound(f'{Path(*parts)} is not inside a bev repository')
        if len(configs) > 1:
            raise InconsistentRepositories(f'This vcs repository contains multiple bev repositories: {configs}')

        return cls(configs[0].parent)

    @property
    def current_version(self) -> CommittedVersion:
        return self.latest_version()

    def latest_version(self, path: PathLike = '.') -> CommittedVersion:
        path = Path(path)
        if not (self.root / path).exists() and not is_hash(path):
            path = to_hash(path)

        if not (self.root / path).exists():
            raise FileNotFoundError(path)

        return call_git(f'git log -n 1 --pretty=format:%H -- {path}', self.root)

    def resolve(self, *parts: PathLike, version: Version = None, fetch: bool = None) -> Path:
        version = self._resolve_version(version)
        key = self.get_key(*parts, version=version, fetch=fetch)
        return self.storage.get_path(key, self._resolve_fetch(fetch))

    def glob(self, *parts: PathLike, version: Version = None, fetch: bool = None) -> Sequence[Path]:
        version = self._resolve_version(version)
        h = self._split(Path(*parts), version)
        if not isinstance(h, TreeHash):
            raise ValueError('`glob` is only applicable to tree hashes')

        pattern = str(h.relative)
        tree = self._load(load_tree, h.key, fetch)

        files = set(tree)
        for file in tree:
            files.update(map(str, list(Path(file).parents)[:-1]))
        files = sorted(files)

        return [h.root / file for file in glob.globfilter(files, pattern, flags=glob.GLOBSTAR)]

    # TODO: cache this based on path parents
    def get_key(self, *parts: PathLike, version: Version = None, fetch: bool = None) -> Key:
        version = self._resolve_version(version)
        h = self._split(Path(*parts), version)
        if isinstance(h, FileHash):
            return h.key

        assert isinstance(h, TreeHash), h
        relative = str(h.relative)
        tree = self._get_tree(h.key, version, fetch)
        if relative not in tree:
            raise HashNotFound(relative)

        return tree[relative]

    def load_tree(self, path: PathLike, version: Version = None, fetch: bool = None) -> dict:
        version = self._resolve_version(version)
        key = self._get_hash(Path(path), version)
        if key is None:
            raise HashNotFound(path)
        return self._get_tree(key, version, fetch)

    # internal logic

    def _get_tree(self, key, version, fetch):
        # we need the version here, because we want to cache only a committed tree
        if version == Local:
            return self._load(load_tree, key, fetch)
        return self._load_cached_tree(key, fetch)

    @lru_cache(None)
    def _load_cached_tree(self, key, fetch):
        return self._load(load_tree, key, fetch=fetch)

    def _get_hash(self, path: Path, version: Version):
        if version == Local:
            return self._get_uncomitted_hash(path)
        return self._get_committed_hash(path, version)

    def _get_uncomitted_hash(self, relative: Path):
        path = self.root / relative
        if path.exists():
            return load_tree_key(path)

    @lru_cache(None)
    def _get_committed_hash(self, relative: Path, version: str):
        assert isinstance(version, str), type(version)
        relative = str(relative)
        if not relative.startswith('./'):
            relative = f'./{relative}'

        try:
            return strip_tree(call_git(f'git show {version}:{relative}', self.root))
        except subprocess.CalledProcessError:
            pass

    def _load(self, func, key, fetch):
        fetch = self._resolve_fetch(fetch)
        return self.storage.load(func, key, fetch=fetch)

    def _split(self, path: Path, version: Version):
        # TODO: use bin-search?
        for parent in list(reversed(path.parents))[1:]:
            hash_path = to_hash(parent)
            key = self._get_hash(hash_path, version)
            if key is not None:
                key = strip_tree(key)
                return TreeHash(key, parent, hash_path, path.relative_to(parent))

        hash_path = to_hash(path)
        key = self._get_hash(hash_path, version)
        if key is None:
            raise HashNotFound(path)

        return FileHash(key, path, hash_path)

    def _resolve_fetch(self, fetch):
        if fetch is None:
            return self._fetch
        return fetch

    def _resolve_version(self, version):
        if version is None:
            version = self._version
        if version is None:
            raise ValueError('The argument `version` must be provided.')
        return version
