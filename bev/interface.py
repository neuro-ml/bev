import inspect
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Sequence, Union

from tarn.digest import digest_value
from wcmatch.glob import GLOBSTAR

from .compat import cached_property
from .config import CONFIG, build_storage, find_vcs_root
from .exceptions import HashNotFound, InconsistentHash, InconsistentRepositories, NameConflict, RepositoryNotFound
from .hash import Key, is_hash, is_tree, load_key, load_tree, strip_tree, to_hash
from .local import Local
from .utils import PathOrStr
from .vc import VC, CommittedVersion, SubprocessGit, Version
from .wc import BevLocalGlob, BevVCGlob


_NoArg = object()


class Repository:
    """
    Interface that represents a `bev` repository.

    Parameters
    ----------
    root:
        the path to the repository's root, i.e. the folder that contains `.bev.yml`
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

    def __init__(self, *root: PathOrStr, fetch: bool = True, version: Optional[Version] = None, check: bool = False):
        self.root = Path(*root)
        self.prefix = Path()
        self.vc: VC = SubprocessGit(self.root)
        self.fetch, self.version, self.check = fetch, version, check
        self._cache = {}

    @property
    def storage(self):
        return self._built[0]

    @property
    def cache(self):
        return self._built[1]

    def copy(self, fetch: bool = _NoArg, version: Optional[Version] = _NoArg, check: bool = _NoArg,
             prefix: PathOrStr = _NoArg, cache: dict = _NoArg):
        result = type(self)(
            self.root, fetch=_resolve_arg(self.fetch, fetch), version=_resolve_arg(self.version, version),
            check=_resolve_arg(self.check, check),
        )
        result.prefix = Path(_resolve_arg(self.prefix, prefix))
        result._cache = _resolve_arg(self._cache, cache)
        return result

    @classmethod
    def from_here(cls, *relative: PathOrStr, fetch: bool = True, version: Optional[Version] = None,
                  check: Optional[bool] = None) -> 'Repository':
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

    def latest_version(self, path: PathOrStr = '.', *, default=inspect.Parameter.empty) -> CommittedVersion:
        """
        Get the last commit given the relative `path`.
        """
        path = self._resolve_relative(path)
        if not (self.root / path).exists() and not is_hash(path):
            path = to_hash(path)

        version = self.vc.get_version(str(path))
        if version is None:
            if default is inspect.Parameter.empty:
                raise FileNotFoundError(f'The path "{path}" is not present in any commit')

            return default

        return version

    def resolve(self, *parts: PathOrStr, version: Optional[Version] = None, fetch: Optional[bool] = None,
                check: Optional[bool] = None) -> Path:
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
            if True - the file's hash will be additionally checked for consistency
        """

        def _resolve(path):
            if check:
                digest = digest_value(path, self.storage.algorithm).hex()
                if digest != key:
                    raise InconsistentHash(
                        f'The path "{Path(*parts)}" has a wrong hash: expected "{key}", actual "{digest}"'
                    )

            return path

        relative = self._resolve_relative(*parts)
        version = self._resolve_version(version)
        fetch = self._resolve_fetch(fetch)
        check = self._resolve_check(check)

        absolute = self.root / relative
        if version == Local and absolute.exists():
            if to_hash(absolute).exists():
                raise NameConflict(f'Both the path "{relative}" and its hash "{to_hash(relative)}" found')
            return absolute.resolve()

        key = self.get_key(*parts, version=version, fetch=fetch)
        return self.storage.read(_resolve, key, fetch=fetch)

    def glob(self, *parts: PathOrStr, version: Optional[Version] = None,
             fetch: Optional[bool] = None) -> Sequence[Path]:
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
        fetch = self._resolve_fetch(fetch)
        pattern = os.path.join(*parts)

        if version == Local:
            glob = BevLocalGlob(pattern, self.root, self.prefix, self.storage, fetch, GLOBSTAR)
        else:
            glob = BevVCGlob(
                pattern, self.root, self.prefix, version, self._cache, self.vc, self.storage, fetch, GLOBSTAR
            )

        return list(map(Path, glob.glob()))

    # TODO: cache this based on path parents
    def get_key(self, *parts: PathOrStr, version: Optional[Version] = None, fetch: Optional[bool] = None,
                error: bool = True) -> Union[Key, None]:
        version = self._resolve_version(version)
        path = self._resolve_relative(*parts)
        try:
            h = self._split(path, version)
        except HashNotFound:
            if error:
                raise
            return None

        if isinstance(h, Key):
            return h

        h, relative = h
        if relative == '.':
            raise HashNotFound(f'"{path}" is a hashed folder')

        tree = self._get_tree(h, version, fetch)
        if relative not in tree:
            if relative in self._expand_folders(tree):
                raise HashNotFound(f'"{path}" is a folder inside a tree hash')

            if error:
                raise HashNotFound(str(path))
            return None

        return tree[relative]

    def load_tree(self, path: PathOrStr, version: Optional[Version] = None, fetch: Optional[bool] = None) -> dict:
        path = self._resolve_relative(path)
        version = self._resolve_version(version)
        key = self._get_hash(Path(path), version)
        if key is None:
            raise HashNotFound(path)

        key = strip_tree(key)
        return self._get_tree(key, version, fetch)

    # navigation

    def __truediv__(self, other: PathOrStr):
        other = Path(other)
        if other.is_absolute():
            raise ValueError('Only relative paths are supported')

        prefix = self.prefix / other
        return self.copy(prefix=prefix)

    @property
    def path(self):
        return self.root / self.prefix

    # internal logic

    @cached_property
    def _built(self):
        return build_storage(self.root)

    def _get_tree(self, key, version, fetch):
        # we need the version here, because we want to cache only a committed tree
        if version == Local:
            return self._load(load_tree, key, fetch)
        return self._load_cached_tree(key, fetch)

    @lru_cache(None)
    def _load_cached_tree(self, key, fetch):
        return self._load(load_tree, key, fetch=fetch)

    def _get_hash(self, relative: PathOrStr, version: Version):
        if version == Local:
            path = self.root / relative
            if path.exists():
                return load_key(path)
            return

        else:
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
                return key, str(path.relative_to(parent))

        hash_path = to_hash(path)
        key = self._get_hash(hash_path, version)
        if key is None:
            raise HashNotFound(path)

        if is_tree(key):
            return key, '.'

        return key

    def _resolve_check(self, check):
        if check is None:
            return self.check
        return check

    def _resolve_fetch(self, fetch):
        if fetch is None:
            return self.fetch
        return fetch

    def _resolve_version(self, version) -> Version:
        if version is None:
            version = self.version
        if version is None:
            raise ValueError('The argument `version` must be provided')
        return version

    def _resolve_relative(self, *parts):
        if not parts:
            return self.prefix
        return self.prefix / Path(*parts)

    @staticmethod
    def _expand_folders(tree) -> set:
        result = set(tree)
        for file in tree:
            result.update(map(str, list(Path(file).parents)[:-1]))
        return result


def _resolve_arg(x, y):
    return x if y is _NoArg else y
