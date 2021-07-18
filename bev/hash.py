import json
from pathlib import Path
from typing import NamedTuple

Key = str


def is_hash(path: Path):
    return path.name.endswith('.hash')


def to_hash(path: Path):
    assert not is_hash(path)
    return path.with_name(f'{path.name}.hash')


def from_hash(path: Path):
    assert is_hash(path)
    return path.with_name(path.stem)


class FileHash(NamedTuple):
    key: Key
    path: Path
    hash: Path


class TreeHash(NamedTuple):
    key: Key
    root: Path
    hash: Path
    relative: Path


def load_key(path: Path):
    with open(path, 'r') as file:
        return file.read().strip()


def load_tree(path: Path):
    with open(path, 'r') as file:
        return json.load(file)


# FIXME: the names are misleading
def load_tree_key(path: Path):
    with open(path) as file:
        return strip_tree(file.read().strip())


def strip_tree(key):
    if key.startswith('tree:'):
        key = key[5:]
    elif key.startswith('T:'):
        key = key[2:]
    return key
