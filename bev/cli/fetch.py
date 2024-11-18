from pathlib import Path
from typing import List

import typer
from rich.progress import track
from typing_extensions import Annotated

from ..exceptions import HashError, HashNotFound
from ..hash import from_hash, is_hash, is_tree, load_key, load_tree, strip_tree, to_hash
from ..interface import Repository
from ..shortcuts import get_consistent_repo
from .app import app_command


def _fetch(repo: Repository, path: Path):
    key = load_key(path)
    if is_tree(key):
        key = strip_tree(key)
        keys = sorted(set(map(bytes.fromhex, repo.storage.read(load_tree, key, fetch=True).values())))
    else:
        keys = [bytes.fromhex(key)]

    desc = str(from_hash(path))
    if len(desc) > 30:
        desc = desc[:27] + '...'

    missing = {k for k, success in track(repo.storage.fetch(keys), description=desc, total=len(keys)) if not success}
    if missing:
        raise HashNotFound(f'Could not fetch {len(missing)} key(s) from remote')


@app_command
def fetch(
        paths: Annotated[List[Path], typer.Argument(
            help='The paths to fetch', show_default='The current directory'
        )] = None,
        repository: Annotated[Path, typer.Option(
            '--repository', '--repo', help='The bev repository. It is usually detected automatically',
            show_default=False,
        )] = None
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
