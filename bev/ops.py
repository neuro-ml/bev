from enum import Enum
from pathlib import Path
from typing import Union, Callable

from tarn import Storage

from .config import identity
from .hash import is_hash, load_key, is_tree, load_tree, from_hash, strip_tree, normalize_tree, HashType, tree_to_hash
from .interface import Repository
from .utils import PathOrStr


class Conflict(Enum):
    # add new entries, check for collisions
    update = 'update'
    # overwrite everything
    override = 'override'
    # remove the previous value
    replace = 'replace'
    # no previous value should exist
    error = 'error'


def gather(source: PathOrStr, storage: Union[Storage, Repository], progressbar: Callable = identity) -> HashType:
    source = Path(source)
    if not source.exists():
        # TODO
        raise FileNotFoundError(source)

    if isinstance(storage, Repository):
        storage = storage.storage

    if is_hash(source):
        key = load_key(source)
        if is_tree(key):
            gathered = normalize_tree(storage.read(load_tree, strip_tree(key)), storage.digest_size)
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
                            key = storage.read(load_tree, strip_tree(key))

                        gathered[from_hash(relative)] = key

                    else:
                        gathered[relative] = storage.write(child)

            gathered = normalize_tree(gathered, storage.digest_size)

        else:
            assert source.is_file()
            gathered = storage.write(source)

    return gathered


def load_hash(path: PathOrStr, storage) -> HashType:
    key = load_key(path)
    if is_tree(key):
        return normalize_tree(storage.read(load_tree, strip_tree(key)), storage.digest_size)
    return key


def save_hash(tree: HashType, path: PathOrStr, storage: Union[Storage, Repository]):
    if isinstance(storage, Repository):
        storage = storage.storage
    if isinstance(tree, dict):
        tree = tree_to_hash(tree, storage)

    with open(path, 'w') as file:
        file.write(tree)
    return tree
