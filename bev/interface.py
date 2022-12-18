import inspect
import os
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Sequence, Union

from tarn.digest import digest_file
from wcmatch.glob import GLOBSTAR

from .config import CONFIG, build_storage, find_vcs_root
from .exceptions import RepositoryNotFound, HashNotFound, InconsistentHash, NameConflict, InconsistentRepositories
from .hash import is_hash, to_hash, load_tree, load_tree_key, strip_tree, FileHash, InsideTreeHash, Key
from .local import Local
from .utils import PathOrStr
from .vc import Version, CommittedVersion, VC, SubprocessGit
from .wc import BevLocalGlob, BevVCGlob


class Repository:
    """
    Interface that represents a `bev` repository.

    Parameters
    ----------
    root:
        the path to the repository's root, i.e. the folder that contains `.bev.config`
    fetch: bool
        whether to fetch files from remote locations when needed.
        Can be overridden in corresponding methods
    version: str, Local
        default value for data version. Can be either a string with a commit hash/tag or the `Local` object, which
        means that the local (possibly uncommitted) version of the files will be used.
        Can be overridden in corresponding methods
    check: bool
        default value for `resolve` mode. If True - the file's hash will be additionally checked for consistency.
        Can be overridden in corresponding methods
    """

    def __init__(self, *root: PathOrStr, fetch: bool = True, version: Version = None, check: bool = False):
        self.root = Path(*root)
        self.prefix = Path()
        self.storage, self.cache = build_storage(self.root)
        self.vc: VC = SubprocessGit(self.root)
        self._fetch, self._version, self._check = fetch, version, check
        self._cache = {}

    @classmethod
    def from_here(cls, *relative: PathOrStr, fetch: bool = True, version: Version = None,
                  check: bool = None) -> 'Repository':
        """
        Creates a repository with a path `relative` to the file in which this method is called.

        Examples
        --------
        >>> repo = Repository.from_here('../../data')
        """
        file = Path(inspect.stack()[1].filename)
        return cls(file.parent / Path(*relative), fetch=fetch, version=version, check=check)

    @classmethod
    def from_vcs(cls, *parts: PathOrStr) -> 'Repository':
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
        warnings.warn('This property is deprecated, use `latest_version()` instead', DeprecationWarning)
        return self.latest_version()

    def latest_version(self, path: PathOrStr = '.', *, default=inspect.Parameter.empty) -> CommittedVersion:
        """
        Get the last commit given the relative `path`.
        """
        path = self._normalize_relative(path)
        if not (self.root / path).exists() and not is_hash(path):
            path = to_hash(path)

        version = self.vc.get_version(str(path))
        if version is None:
            if default is inspect.Parameter.empty:
                raise FileNotFoundError(f'The path "{path}" is not present in any commit')

            return default

        return version

    def resolve(self, *parts: PathOrStr, version: Version = None, fetch: bool = None, check: bool = None) -> Path:
        """
        Get the real path of a file in the repository

        Parameters
        ----------
        parts: str, Path
            the path to the file in the repository
        fetch: bool
            whether to fetch files from remote locations when needed
        version: str, Local
            the data version. Can be either a string with a commit hash/tag or the `Local` object, which
            means that the local (possibly uncommitted) version of the files will be used
        check: bool
            default value for `resolve` mode. If True - the file's hash will be additionally checked for consistency
        """

        def _resolve(path):
            if check:
                digest = digest_file(path, self.storage.algorithm)
                if digest != key:
                    raise InconsistentHash(
                        f'The path "{Path(*parts)}" has a wrong hash: expected "{key}", actual "{digest}"'
                    )

            return path

        relative = self._normalize_relative(*parts)
        version = self._resolve_version(version)
        absolute = self.root / relative
        if version == Local and absolute.exists():
            if to_hash(absolute).exists():
                raise NameConflict(f'Both the path "{relative}" and its hash "{to_hash(relative)}" found')
            return absolute.resolve()

        check = self._resolve_check(check)
        key = self.get_key(relative, version=version, fetch=fetch)
        return self.storage.read(_resolve, key, fetch=self._resolve_fetch(fetch))

    def glob(self, *parts: PathOrStr, version: Version = None, fetch: bool = None) -> Sequence[Path]:
        """
        Get all the paths in the repository that match a given pattern

        Parameters
        ----------
        parts: str, Path
            the pattern to match
        fetch: bool
            whether to fetch files from remote locations when needed
        version: str, Local
            the data version. Can be either a string with a commit hash/tag or the `Local` object, which
            means that the local (possibly uncommitted) version of the files will be used
        """
        version = self._resolve_version(version)
        pattern = os.path.join(*parts)

        if version == Local:
            glob = BevLocalGlob(pattern, self.root, self.prefix, self.storage, fetch, GLOBSTAR)
        else:
            glob = BevVCGlob(
                pattern, self.root, self.prefix, version, self._cache, self.vc, self.storage, fetch, GLOBSTAR
            )

        return list(map(Path, glob.glob()))

    # TODO: cache this based on path parents
    def get_key(self, *parts: PathOrStr, version: Version = None, fetch: bool = None,
                error: bool = True) -> Union[Key, None]:
        version = self._resolve_version(version)
        path = self._normalize_relative(*parts)
        try:
            h = self._split(path, version)
        except HashNotFound:
            if error:
                raise
            return None

        if isinstance(h, FileHash):
            return h.key

        assert isinstance(h, InsideTreeHash), h
        relative = str(h.relative)
        tree = self._get_tree(h.key, version, fetch)
        if relative not in tree:
            if relative in self._expand_folders(tree):
                raise HashNotFound(f'"{str(path)}" is a folder inside a tree hash')

            if error:
                raise HashNotFound(str(path))
            return None

        return tree[relative]

    def load_tree(self, path: PathOrStr, version: Version = None, fetch: bool = None) -> dict:
        path = self._normalize_relative(path)
        version = self._resolve_version(version)
        key = self._get_hash(Path(path), version)
        if key is None:
            raise HashNotFound(path)

        key = strip_tree(key)
        return self._get_tree(key, version, fetch)

    # navigation

    def __truediv__(self, other: Union[str, Path]):
        other = Path(other)
        if other.is_absolute():
            raise ValueError('Only relative paths are supported')

        child = Repository(self.root, fetch=self._fetch, version=self._version, check=self._check)
        # FIXME
        child.prefix = self.prefix / other
        child._cache = self._cache
        return child

    @property
    def path(self):
        return self.root / self.prefix

    # internal logic

    def _normalize_relative(self, *parts):
        # TODO: check that it's not a hash path
        return self.prefix / Path(*parts)

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
    def _get_committed_hash(self, relative: Path, version: CommittedVersion):
        assert isinstance(version, CommittedVersion), type(version)
        return self.vc.read(str(relative), version)

    def _load(self, func, key, fetch):
        fetch = self._resolve_fetch(fetch)
        return self.storage.read(func, key, fetch=fetch)

    def _split(self, path: Path, version: Version):
        # TODO: use bin-search?
        for parent in list(reversed(path.parents))[1:]:
            hash_path = to_hash(parent)
            key = self._get_hash(hash_path, version)
            if key is not None:
                key = strip_tree(key)
                return InsideTreeHash(key, parent, hash_path, path.relative_to(parent))

        hash_path = to_hash(path)
        key = self._get_hash(hash_path, version)
        if key is None:
            raise HashNotFound(path)

        return FileHash(key, path, hash_path)

    def _resolve_check(self, check):
        if check is None:
            return self._check
        return check

    def _resolve_fetch(self, fetch):
        if fetch is None:
            return self._fetch
        return fetch

    def _resolve_version(self, version):
        if version is None:
            version = self._version
        if version is None:
            raise ValueError('The argument `version` must be provided')
        return version

    @staticmethod
    def _expand_folders(tree) -> set:
        result = set(tree)
        for file in tree:
            result.update(map(str, list(Path(file).parents)[:-1]))
        return result
