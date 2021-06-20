import json
import shutil
import os
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from ..interface import Repository
from ..config import get_current_repo
from ..hash import is_hash, to_hash


def validate_file(path: Path):
    assert path.is_file()
    if is_hash(path):
        raise ValueError('You are trying to add a hash to the storage.')

    return path


def save_tree(repo: Repository, tree: dict, destination: Path):
    # save the directory description
    # making sure that each time the same string will be saved
    tree = OrderedDict((k, tree[k]) for k in sorted(tree))
    tree_path = destination.parent / f'{destination.name}.hash.temp'

    # TODO: storage should allow writing directly from memory
    with open(tree_path, 'w') as file:
        json.dump(tree, file)
    key = repo.storage.store(tree_path)
    os.remove(tree_path)

    with open(destination, 'w') as file:
        file.write(f'tree:{key}')

    return key


def add_file(repo: Repository, source: Path, destination: Optional[Path], keep: bool):
    validate_file(source)
    key = repo.storage.store(source)

    if destination is not None:
        assert is_hash(destination)
        with open(destination, 'w') as file:
            file.write(key)

    if not keep:
        os.remove(source)

    return key


def add_folder(repo: Repository, source: Path, destination: Optional[Path], keep: bool):
    assert source.is_dir()

    tree = {}
    files = [file for file in source.glob('**/*') if not file.is_dir()]
    for file in tqdm(files):
        relative = file.relative_to(source)
        tree[str(relative)] = add_file(repo, file, None, True)

    result = tree
    if destination is not None:
        result = save_tree(repo, tree, destination)
    if not keep:
        shutil.rmtree(source)

    return result


def add(source: str, destination: str, keep: bool, context: str = '.'):
    repo = get_current_repo(context)
    source = Path(source)

    if destination is None:
        destination = source.parent
    else:
        destination = Path(destination)

    destination /= to_hash(source).name
    if destination.exists():
        raise FileExistsError(destination)

    if source.is_dir():
        add_folder(repo, source, destination, keep)
    else:
        add_file(repo, source, destination, keep)
