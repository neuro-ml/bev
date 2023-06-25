from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Union

from tarn import HashKeyStorage

from .config.utils import identity
from .hash import HashType, from_hash, is_hash, is_tree, load_key, load_tree, normalize_tree, strip_tree, tree_to_hash
from .interface import Repository
from .utils import PathOrStr


class Conflict(Enum):
    """
    Conflict resolution policy, in case the destination already exists:

    update - add new entries and check for collisions
    override - add new entries, overwrite the colliding parts
    replace - remove the previous entries
    error - no previous entries should exist
    """
    update = 'update'
    override = 'override'
    replace = 'replace'
    error = 'error'


def gather(source: PathOrStr, storage: Union[HashKeyStorage, Repository], progressbar: Callable = identity,
           fetch: Optional[bool] = None) -> HashType:
    source = Path(source)
    if not source.exists():
        # TODO
        raise FileNotFoundError(source)

    if isinstance(storage, Repository):
        if fetch is None:
            fetch = storage.fetch
        storage = storage.storage

    if is_hash(source):
        key = load_key(source)
        if is_tree(key):
            gathered = normalize_tree(storage.read(load_tree, strip_tree(key), fetch=fetch), storage.digest_size)
        else:
            gathered = key

    else:
        if source.is_dir():
            gathered = {}
            for child in progressbar(source.glob('**/*')):
                relative = child.relative_to(source)
                if not child.is_dir():
                    if is_hash(child):
                        key = load_key(child)
                        if is_tree(key):
                            key = storage.read(load_tree, strip_tree(key), fetch=fetch)

                        gathered[from_hash(relative)] = key

                    else:
                        gathered[relative] = storage.write(child).hex()

            gathered = normalize_tree(gathered, storage.digest_size)

        else:
            assert source.is_file()
            gathered = storage.write(source).hex()

    return gathered


def load_hash(path: PathOrStr, storage, fetch: bool = False) -> HashType:
    key = load_key(path)
    if is_tree(key):
        return normalize_tree(storage.read(load_tree, strip_tree(key), fetch=fetch), storage.digest_size)
    return key


def save_hash(tree: HashType, path: PathOrStr, storage: Union[HashKeyStorage, Repository]):
    if isinstance(storage, Repository):
        storage = storage.storage
    if isinstance(tree, dict):
        tree = tree_to_hash(tree, storage)

    with open(path, 'w') as file:
        file.write(tree)
    return tree
