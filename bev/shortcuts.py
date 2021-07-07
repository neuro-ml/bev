from typing import Sequence
from bev.config import CONFIG, find_repo_root
from bev.interface import Repository
from bev.utils import InconsistentRepositories, PathLike, RepositoryNotFound


def get_current_repo(path: PathLike = '.') -> Repository:
    root = find_repo_root(path)
    if root is None:
        raise RepositoryNotFound(f'{CONFIG} files not found in current folder\'s parents')

    return Repository.from_root(root)


def get_consistent_repo(paths: Sequence[PathLike]) -> Repository:
    roots = set(filter(None, map(find_repo_root, paths)))
    if len(roots) > 1:
        raise InconsistentRepositories('The paths are located in different repositories')
    if not roots:
        raise RepositoryNotFound(f'{CONFIG} files not found among folder\'s parents')

    return Repository.from_root(roots.pop())
