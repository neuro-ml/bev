import json
import os
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Dict, NamedTuple, Union

from tarn import HashKeyStorage
from tarn.utils import value_to_buffer

from .exceptions import HashError
from .utils import PathOrStr


Key = str
Tree = Dict[PathOrStr, Union[Key, Dict]]
HashType = Union[Key, Tree]


def is_hash(path: PathOrStr):
    return Path(path).name.endswith('.hash')


def to_hash(path: PathOrStr):
    path = Path(path)
    if is_hash(path):
        raise HashError('The path is already a hash')
    return path.with_name(f'{path.name}.hash')


def from_hash(path: PathOrStr):
    path = Path(path)
    if not is_hash(path):
        raise HashError('The path is already not a hash')
    return path.with_name(path.stem)


def is_tree(key: Key):
    return key.startswith('T:')


def load_key(path: PathOrStr):
    with open(path, 'r') as file:
        return file.read().strip()


def load_tree(path: Path):
    with value_to_buffer(path) as buffer:
        return json.load(buffer)


def strip_tree(key):
    if key.startswith('T:'):
        key = key[2:]
    return key


def tree_to_hash(tree: Tree, storage: HashKeyStorage):
    tree = normalize_tree(tree, storage.digest_size)
    # making sure that each time the same string will be saved
    tree = OrderedDict((k, tree[k]) for k in sorted(map(os.fspath, tree)))
    with tempfile.TemporaryDirectory() as tmp:
        tree_path = Path(tmp, 'hash')
        # TODO: storage should allow writing directly from memory
        with open(tree_path, 'w') as file:
            json.dump(tree, file)

        return 'T:' + storage.write(tree_path).hex()


def normalize_tree(tree: Tree, digest_size: int):
    def flatten(x):
        for key, value in x.items():
            key = Path(os.fspath(key))

            if isinstance(value, str):
                if len(value) != digest_size * 2:
                    # TODO
                    raise ValueError(value)

                yield key, value

            elif isinstance(value, dict):
                for k, v in flatten(value):
                    yield key / k, v

            else:
                # TODO
                raise TypeError(value)

    # TODO: detect absolute paths
    result = {}
    for path, hash_ in flatten(tree):
        path = os.fspath(path)
        if path in result and result[path] != hash_:
            # TODO
            raise ValueError

        # TODO: check digest size and type
        result[path] = hash_

    # TODO: detect folders that have hashes
    return result


class FileHash(NamedTuple):
    key: Key
    path: Path
    hash: Path


class TreeHash(NamedTuple):
    key: Key
    path: Path
    hash: Path


class InsideTreeHash(NamedTuple):
    key: Key
    root: Path
    hash: Path
    relative: Path
