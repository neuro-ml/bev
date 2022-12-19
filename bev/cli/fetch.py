from typing import List
from pathlib import Path

import typer
from rich.progress import track

from ..exceptions import HashError
from ..interface import Repository
from ..shortcuts import get_consistent_repo
from ..hash import is_hash, to_hash, load_tree, load_key, strip_tree, is_tree, from_hash
from ..utils import HashNotFound
from .app import app_command


def _fetch(repo: Repository, path: Path):
    if not is_hash(path):
        path = to_hash(path)

    key = load_key(path)
    if is_tree(key):
        key = strip_tree(key)
        keys = list(set(repo.storage.read(load_tree, key).values()))
    else:
        keys = [key]

    desc = f'Fetching {from_hash(path)}'
    if len(desc) > 30:
        desc = desc[:27] + '...'

    missing = set(keys) - set(track(
        repo.storage.fetch(keys, verbose=False, legacy=False),
        description=desc, total=len(keys),
    ))
    if missing:
        raise HashNotFound(f'Could not fetch {len(missing)} key(s) from remote')


@app_command
def fetch(
        paths: List[Path] = typer.Argument(None, help='The paths to fetch', show_default='The current directory'),
        repository: Path = typer.Option(
            None, '--repository', '--repo', help='The bev repository. It is usually detected automatically',
            show_default=False,
        )
):
    """Fetch the missing values from remote, if possible"""
    paths = paths or [Path('.')]
    if repository is None:
        repository = '.'

    repo = get_consistent_repo([repository, *paths])
    for path in paths:
        if is_hash(path):
            _fetch(repo, path)
        elif not path.exists():
            _fetch(repo, to_hash(path))
        elif path.is_dir():
            for file in path.glob('**/*'):
                if file.is_file() and is_hash(file):
                    _fetch(repo, file)
        else:
            raise HashError(f'Cannot fetch "{path}" - it is not a hash nor a folder')
