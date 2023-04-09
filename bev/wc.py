from pathlib import Path
from typing import AnyStr, Iterator, NamedTuple, Optional, Sequence, Tuple

from wcmatch.glob import Glob

from .exceptions import NameConflict
from .hash import from_hash, is_hash, is_tree, load_key, load_tree, strip_tree, to_hash
from .vc import VC, TreeEntry


class DirEntry(NamedTuple):
    name: AnyStr
    is_dir: bool
    is_hidden: bool
    is_symlink: bool


class BaseGlob(Glob):
    def _scandir(self, curdir: Optional[AnyStr]) -> Iterator[DirEntry]:
        """Return the (non-recursive) contents of a directory."""
        raise NotImplementedError

    def _lexists(self, path: AnyStr) -> bool:
        """Check if file exists."""
        raise NotImplementedError

    def _iter(self, curdir: Optional[AnyStr], dir_only: bool, deep: bool) -> Iterator[Tuple[AnyStr, bool, bool, bool]]:
        """Iterate the directory."""
        for special in self.specials:
            yield special, True, True, False

        for entry in self._scandir(curdir):
            # this will allow us to ignore the restriction in _scandir
            if not dir_only or entry.is_dir:
                yield entry


class BevGlob(BaseGlob):
    def __init__(self, pattern, repo_root, relative, version, cache: dict, storage, fetch, flags: int):
        super().__init__(pattern, flags, Path(repo_root, relative))
        self._cache = cache
        self._version = version
        self._repo_root = Path(repo_root)
        self._storage = storage
        self._fetch = fetch

    def _list_dir(self, relative: Path) -> Sequence[Path]:
        """ Return the contents of a directory `relative` to `self._repo_root` """
        raise NotImplementedError

    def _exists(self, relative: Path) -> bool:
        """ Whether the path `relative` to `self._repo_root` exists """
        raise NotImplementedError

    def _read_tree_key(self, relative: Path):
        """ Read a tree key located `relative` to `self._repo_root` """
        raise NotImplementedError

    def _get_cached(self, relative: Path):
        for parent in relative.parents:
            if (self._version, parent) in self._cache:
                cache = self._cache[self._version, parent]
                for part in relative.relative_to(parent).parts:
                    assert part in cache, (part, relative)
                    cache = cache[part]

                return cache

        if (self._version, relative) in self._cache:
            return self._cache[self._version, relative]

    def _set_cached(self, relative: Path, value):
        self._cache[self._version, relative] = value

    @staticmethod
    def _normalize_tree(raw: dict):
        tree = {}
        for path, value in raw.items():
            *parents, name = Path(path).parts
            subtree = tree
            for parent in parents:
                subtree = subtree.setdefault(parent, {})

            subtree[name] = value

        return tree

    def _lexists(self, path: AnyStr) -> bool:
        relative = Path(self.root_dir, path).relative_to(self._repo_root)
        return (
                self._get_cached(relative) is not None
                or self._exists(relative)
                or self._exists(to_hash(relative))
        )

    def _scandir(self, curdir: Optional[AnyStr]) -> Iterator[DirEntry]:
        current = Path(self.root_dir)
        if curdir:
            current /= curdir
        relative = current.relative_to(self._repo_root)

        # is it already cached?
        cached = self._get_cached(relative)
        if cached is None and relative.parts:
            key = self._read_tree_key(to_hash(relative))
            if key is not None:
                assert not self._exists(relative), relative
                assert is_tree(key), (key, relative)

                cached = self._normalize_tree(self._storage.read(load_tree, strip_tree(key), fetch=self._fetch))
                self._set_cached(relative, cached)

        # is it a hashed folder?
        if cached:
            assert isinstance(cached, dict), cached
            for name, value in cached.items():
                yield DirEntry(name, isinstance(value, dict), self._is_hidden(name), False)

        else:
            # it's a real folder
            for entry in self._list_dir(relative):
                relative_path = relative / entry.name
                if is_hash(relative_path):
                    relative_plain = from_hash(relative_path)
                    if self._exists(relative_plain):
                        raise NameConflict(
                            f'Both the path "{relative_plain}" and its hash "{relative_path}" found'
                        )

                    key = self._read_tree_key(relative_path)
                    assert key is not None, relative_path
                    is_dir = is_tree(key)
                    if is_dir:
                        cached = self._normalize_tree(self._storage.read(load_tree, strip_tree(key), fetch=self._fetch))
                        self._set_cached(relative_plain, cached)
                    else:
                        self._set_cached(relative_plain, key)

                    yield DirEntry(relative_plain.name, is_dir, self._is_hidden(relative_plain.name), False)

                else:
                    yield DirEntry(entry.name, entry.is_dir, self._is_hidden(entry.name), entry.is_symlink)


class BevLocalGlob(BevGlob):
    def __init__(self, pattern, repo_root, relative, storage, fetch, flags: int):
        super().__init__(pattern, repo_root, relative, None, {}, storage, fetch, flags)

    def _list_dir(self, relative: Path):
        return [
            TreeEntry(entry.name, entry.is_dir(), entry.is_symlink())
            for entry in (self._repo_root / relative).iterdir()
        ]

    def _exists(self, relative: Path):
        return (self._repo_root / relative).exists()

    def _read_tree_key(self, relative: Path):
        path = self._repo_root / relative
        if path.exists():
            return load_key(path)


class BevVCGlob(BevGlob):
    def __init__(self, pattern, repo_root, relative, version, cache, vc: VC, storage, fetch, flags: int):
        super().__init__(pattern, repo_root, relative, version, cache, storage, fetch, flags)
        self._vc = vc

    def _list_dir(self, relative: Path):
        return self._vc.list_dir(str(relative), self._version)

    def _exists(self, relative: Path):
        return relative.name in {x.name for x in self._vc.list_dir(str(relative.parent), self._version)}

    def _read_tree_key(self, relative: Path):
        return self._vc.read(str(relative), self._version)
