import warnings
from functools import wraps
from os import PathLike
import subprocess
import shlex
from typing import Union

from .exceptions import *

PathOrStr = Union[str, PathLike[str]]


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


# legacy
HashNotFoundError = HashNotFound


def deprecate(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        nonlocal warned
        if not warned:
            warnings.warn('This function is deprecated', DeprecationWarning, 2)
            warnings.warn('This function is deprecated', UserWarning, 2)
            warned = True

        return func(*args, **kwargs)

    warned = False
    return decorator
