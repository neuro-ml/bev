from typing import Sequence

from dpipe.io import load_json
from pathlib import Path

from ..config import get_current_repo
from ..hash import is_hash, to_hash


def _fetch(path: str):
    repo = get_current_repo()

    path = Path(path)
    if not is_hash(path):
        path = to_hash(path)

    with open(path) as file:
        key = file.read().strip()

    mapping = repo.storage.load(load_json, key)
    missing = repo.storage.fetch(mapping.values(), verbose=True)
    if missing:
        raise FileNotFoundError(f'Could not fetch {len(missing)} keys from remote.')


def fetch(paths: Sequence[str]):
    list(map(_fetch, paths))
