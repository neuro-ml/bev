import os
import shlex
import subprocess
from abc import abstractmethod
from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple, Sequence, Union

from .config import find_vcs_root
from .local import LocalVersion


CommittedVersion = str
Version = Union[CommittedVersion, LocalVersion]


class TreeEntry(NamedTuple):
    name: str
    is_dir: bool
    is_symlink: bool


class VC:
    def __init__(self, root: Path):
        self.root = root

    @abstractmethod
    def read(self, relative: str, version: CommittedVersion) -> Union[str, None]:
        """
        Get the contents of a file `relative` to the root at a given `version`
        or None, if the file doesn't exist.
        """

    @abstractmethod
    def get_version(self, relative: str, n: int = 0) -> Union[str, None]:
        """
        Get the `n`th version of a file `relative` to the root in reverse chronological order
        or None, if the file doesn't exist.

        E.g. for n=0 - this will be the most recent version.
        """

    @abstractmethod
    def list_dir(self, relative: str, version: CommittedVersion) -> Sequence[TreeEntry]:
        """ Get the contents of a directory `relative` to the root given `version` """


class SubprocessGit(VC):
    def __init__(self, root: Path):
        super().__init__(root)
        self._git_root = None

    @lru_cache(None)
    def read(self, relative: str, version: CommittedVersion) -> Union[str, None]:
        if not relative.startswith('./'):
            relative = f'./{relative}'

        with suppress(subprocess.CalledProcessError):
            return self._call_git(f'git show {version}:{relative}', self.root)

    def get_version(self, relative: str, n: int = 0) -> Union[str, None]:
        if n == 0:
            n = ''
        else:
            n = f'--skip {n}'

        if not relative.startswith('./'):
            relative = f'./{relative}'

        with suppress(subprocess.CalledProcessError):
            return self._call_git(f'git log -n 1 {n} --pretty=format:%H -- {relative}', self.root) or None

    @lru_cache(None)
    def list_dir(self, relative: str, version: CommittedVersion) -> Sequence[TreeEntry]:
        if self._git_root is None:
            self._git_root = find_vcs_root(self.root)
        if self._git_root is None:
            raise FileNotFoundError(f'The folder {self.root} is not inside a git repository')

        git_relative = os.path.normpath(os.fspath((self.root / relative).relative_to(self._git_root)))
        suffix = f':{git_relative}' if git_relative != '.' else ''
        result = []
        try:
            lines = self._call_git(f'git ls-tree {version}{suffix}', self._git_root).splitlines()
        except subprocess.CalledProcessError as e:
            if e.returncode == 128:
                raise FileNotFoundError(f'The object {git_relative} not found for version {version}') from None
            raise

        for line in lines:
            mode, kind, rest = line.split(' ', 2)
            _, name = rest.split('\t')
            result.append(TreeEntry(name, kind == 'tree', kind == 'link'))

        return result

    @staticmethod
    def _call_git(command: str, cwd) -> str:
        return subprocess.check_output(shlex.split(command), cwd=cwd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
