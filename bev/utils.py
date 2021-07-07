from pathlib import Path
import subprocess
import shlex
from typing import Union

PathLike = Union[str, Path]


# TODO: use gitpython
def call_git(command: str, cwd=None) -> str:
    return subprocess.check_output(shlex.split(command), cwd=cwd, stderr=subprocess.DEVNULL).decode('utf-8').strip()


def call(command: str, cwd=None) -> str:
    try:
        return subprocess.check_output(shlex.split(command), cwd=cwd).decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr or e.stdout) from e


class HashNotFound(Exception):
    pass


class RepositoryError(Exception):
    pass


class RepositoryNotFound(RepositoryError):
    pass


class InconsistentRepositories(RepositoryError):
    pass


# legacy
HashNotFoundError = HashNotFound
