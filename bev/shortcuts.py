from pathlib import Path
from typing import Sequence

from .config import CONFIG, find_repo_root
from .exceptions import InconsistentRepositories, RepositoryNotFound
from .interface import Repository
from .utils import PathOrStr


def get_current_repo(path: PathOrStr = '.') -> Repository:
    root = find_repo_root(path)
    if root is None:
        raise RepositoryNotFound(f"{CONFIG} files not found in current folder's parents")

    return Repository(root)


def get_consistent_repo_root(paths: Sequence[PathOrStr]) -> Path:
    roots = set(filter(None, map(find_repo_root, paths)))
    if len(roots) > 1:
        raise InconsistentRepositories('The paths are located in different repositories')
    if not roots:
        raise RepositoryNotFound(f"{CONFIG} files not found among folder's parents")

    return roots.pop()


def get_consistent_repo(paths: Sequence[PathOrStr]) -> Repository:
    return Repository(get_consistent_repo_root(paths))
