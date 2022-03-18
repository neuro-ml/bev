import json
import shutil
import os
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Union, Sequence

from tqdm.auto import tqdm

from ..interface import Repository, PathLike
from ..shortcuts import get_consistent_repo
from ..hash import is_hash, to_hash


def validate_file(path: Path):
    assert path.is_file(), path
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
    key = repo.storage.write(tree_path)
    os.remove(tree_path)

    with open(destination, 'w') as file:
        file.write(f'T:{key}')

    return key


def add_file(repo: Repository, source: Path, destination: Optional[Path], keep: bool):
    validate_file(source)
    key = repo.storage.write(source)

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


def add(source: Union[PathLike, Sequence[PathLike]], destination: PathLike, keep: bool, context: str = '.'):
    if isinstance(source, (str, Path)):
        sources = [Path(source)]
    else:
        sources = list(map(Path, source))

    destination = Path(destination)
    if len(sources) > 1:
        if not destination.exists():
            raise FileNotFoundError('When adding multiple sources the destination must be an existing folder')
        if not destination.is_dir():
            raise ValueError('When adding multiple sources the destination must be an existing folder')
        dst_root = destination
    else:
        if destination.exists():
            if destination.is_dir():
                dst_root = destination
            else:
                dst_root = destination.parent
        else:
            if not destination.parent.exists() or not destination.parent.is_dir():
                raise FileNotFoundError(f'The parent destination directory "{destination.parent}" does not exist')

            dst_root = destination.parent

    sources_root = []
    for source in sources:
        if not source.exists():
            raise FileNotFoundError(source)
        sources_root.append(source.parent)

    repo = get_consistent_repo([context, dst_root, *sources_root])

    for source in sources:
        local_destination = destination
        if local_destination.is_dir():
            local_destination /= to_hash(source).name
        if not is_hash(local_destination):
            local_destination = to_hash(local_destination)
        if local_destination.exists():
            raise FileExistsError(local_destination)

        if source.is_dir():
            add_folder(repo, source, local_destination, keep)
        else:
            add_file(repo, source, local_destination, keep)
