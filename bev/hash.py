import json
from pathlib import Path


def is_hash(path: Path):
    return path.name.endswith('.hash')


def to_hash(path: Path):
    assert not is_hash(path)
    return path.with_name(f'{path.name}.hash')


def from_hash(path: Path):
    assert is_hash(path)
    return path.with_name(path.stem)


def load_tree_hash(path: Path):
    with open(path, 'r') as file:
        return json.load(file)


# FIXME: the names are misleading
def load_tree_key(path: Path):
    with open(path) as file:
        key = file.read().strip()
        if key.startswith('tree:'):
            key = key[5:]
        return key
