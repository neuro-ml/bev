import shutil
from pathlib import Path

from ..config import get_current_repo
from ..hash import is_hash, load_tree_hash, load_tree_key
from .add import add_folder, save_tree


def update(source: str, destination: str, keep: bool, overwrite: bool):
    source, destination = Path(source), Path(destination)
    if not is_hash(destination):
        raise ValueError('The destination must be a hash.')

    repo = get_current_repo()
    key = load_tree_key(source)
    mapping = repo.storage.load(load_tree_hash, key)

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
