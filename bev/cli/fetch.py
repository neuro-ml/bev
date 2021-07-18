from typing import Sequence
from pathlib import Path

from ..interface import Repository
from ..shortcuts import get_consistent_repo
from ..hash import is_hash, to_hash, load_tree, load_key, strip_tree
from ..utils import HashNotFound


def _fetch(repo: Repository, path: Path):
    if not is_hash(path):
        path = to_hash(path)

    key = load_key(path)
    if key.startswith(('T:', 'tree:')):
        key = strip_tree(key)
        keys = repo.storage.load(load_tree, key).values()
    else:
        keys = [key]

    missing = repo.storage.fetch(keys, verbose=True)
    if missing:
        raise HashNotFound(f'Could not fetch {len(missing)} keys from remote.')


def fetch(paths: Sequence[str], context: str = '.'):
    repo = get_consistent_repo([context, *paths])
    for path in paths:
        _fetch(repo, Path(context) / path)
