import shlex
import subprocess
from abc import abstractmethod
from contextlib import suppress
from pathlib import Path
from typing import Union

# from dulwich.object_store import tree_lookup_path
# from dulwich.objects import Commit
# from dulwich.repo import Repo

from .local import LocalVersion

CommittedVersion = str
Version = Union[CommittedVersion, LocalVersion]


class VC:
    def __init__(self, root: Path):
        self.root = root

    @abstractmethod
    def show(self, relative: str, version: CommittedVersion) -> Union[str, None]:
        pass

    @abstractmethod
    def log(self, relative: str, skip: int = 0) -> str:
        pass


class SubprocessGit(VC):
    def show(self, relative: str, version: CommittedVersion) -> str:
        if not relative.startswith('./'):
            relative = f'./{relative}'

        with suppress(subprocess.CalledProcessError):
            return self._call_git(f'git show {version}:{relative}', self.root)

    def log(self, relative: str, skip: int = 0) -> Union[str, None]:
        if skip == 0:
            skip = ''
        else:
            skip = f'--skip {skip}'

        if not relative.startswith('./'):
            relative = f'./{relative}'

        try:
            result = self._call_git(f'git log -n 1 {skip} --pretty=format:%H -- {relative}', self.root)
        except subprocess.CalledProcessError as e:
            raise FileNotFoundError(relative) from e
        if not result:
            raise FileNotFoundError(relative)
        return result

    @staticmethod
    def _call_git(command: str, cwd) -> str:
        return subprocess.check_output(shlex.split(command), cwd=cwd, stderr=subprocess.DEVNULL).decode('utf-8').strip()


# TODO: this interface is not ready yet
class Dulwich(VC):
    def __init__(self, root: Path):
        super().__init__(root)
        self._real_repo = None

    def show(self, relative: str, version: CommittedVersion):
        with suppress(KeyError):
            commit: Commit = self._repo.get_object(version.encode())
            _, h = tree_lookup_path(self._repo.get_object, commit.tree, self._relative(relative))
            return self._repo[h].data.decode().strip()

    def log(self, relative: str, skip: int = 0):
        entries = list(self._repo.get_walker(max_entries=skip + 1, paths=[self._relative(relative)]))
        if len(entries) <= skip:
            raise FileNotFoundError(relative)
        commit: Commit = entries[skip].commit
        return commit.sha().hexdigest()

    def _relative(self, path):
        return str((self.root / path).relative_to(self._repo.path)).encode()

    @property
    def _repo(self):
        if self._real_repo is None:
            self._real_repo = Repo.discover(self.root)
        return self._real_repo
