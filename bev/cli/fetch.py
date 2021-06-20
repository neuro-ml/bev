from typing import Sequence

from pathlib import Path

from ..config import get_current_repo
from ..hash import is_hash, to_hash, load_tree_hash, load_tree_key


def _fetch(repo, path: Path):
    if not is_hash(path):
        path = to_hash(path)

    key = load_tree_key(path)
    mapping = repo.storage.load(load_tree_hash, key)
    missing = repo.storage.fetch(mapping.values(), verbose=True)
    if missing:
        raise FileNotFoundError(f'Could not fetch {len(missing)} keys from remote.')


def fetch(paths: Sequence[str], context: str = '.'):
    repo = get_current_repo(context)
    for path in paths:
        _fetch(repo, Path(context) / path)
