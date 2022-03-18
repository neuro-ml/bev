from pathlib import Path
import subprocess
import shlex
from typing import Union

PathLike = Union[str, Path]


# TODO: use gitpython
def call_git(command: str, cwd=None, wrap=False) -> str:
    try:
        return subprocess.check_output(
            shlex.split(command), cwd=cwd, stderr=subprocess.STD_ERROR_HANDLE if wrap else subprocess.DEVNULL
        ).decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        if wrap:
            raise RuntimeError(e.stderr or e.stdout) from e
        raise


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
