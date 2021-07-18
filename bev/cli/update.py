import shutil
from pathlib import Path

from ..shortcuts import get_consistent_repo
from ..hash import is_hash, load_tree, load_tree_key
from .add import add_folder, save_tree


def update(source: str, destination: str, keep: bool, overwrite: bool):
    source, destination = Path(source), Path(destination)
    if not is_hash(destination):
        raise ValueError('The destination must be a hash.')
    if not source.is_dir():
        raise ValueError('The source must be a folder.')

    repo = get_consistent_repo(['.', source, destination.parent])
    key = load_tree_key(destination)
    mapping = repo.storage.load(load_tree, key)

    new = add_folder(repo, source, None, keep=True)
    common = set(new) & set(mapping)
    mismatch = {k for k in common if new[k] != mapping[k]}
    if mismatch:
        if not overwrite:
            raise ValueError(f'Mismatch between old and new files at following paths: {mismatch}')
        print(f'Mismatched {len(mismatch)} files. Overwriting.')
    if common:
        print(f'{len(common)} files were already present.')

    mapping.update(new)
    save_tree(repo, mapping, destination)
    if not keep:
        shutil.rmtree(source)
