import shutil

from pathlib import Path

from tqdm import tqdm

from ..shortcuts import get_current_repo
from ..hash import is_hash, to_hash, from_hash, load_tree, load_tree_key
from .add import save_tree


def pull(source: str, destination: str, mode: str):
    repo = get_current_repo()

    assert mode in PULL_MODES, mode
    source, destination = Path(source), Path(destination)
    if not is_hash(source):
        source = to_hash(source)

    key = load_tree_key(source)
    mapping = repo.storage.load(load_tree, key)

    for file, value in tqdm(mapping.items()):
        file = destination / file
        file.parent.mkdir(parents=True, exist_ok=True)
        PULL_MODES[mode](value, file, repo)


def save_hash(value, file, repo):
    with open(to_hash(file), 'w') as f:
        f.write(value)


PULL_MODES = {
    'copy': lambda h, dst, repo: repo.storage.load(shutil.copyfile, h, dst),
    'hash': save_hash,
}


def gather(source: str, destination: str):
    repo = get_current_repo()

    source, destination = Path(source), Path(destination)
    if not is_hash(destination):
        destination = to_hash(destination)

    tree = {}
    files = [file for file in source.glob('**/*') if not file.is_dir()]
    for file in tqdm(files):
        assert is_hash(file)
        relative = file.relative_to(source)
        with open(file, 'r') as f:
            tree[str(from_hash(relative))] = f.read()

    save_tree(repo, tree, destination)
