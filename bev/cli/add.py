import json
import os
import shutil
from collections import OrderedDict
from pathlib import Path
from typing import List, Optional

import typer
from rich.progress import track
from tqdm.auto import tqdm

from ..exceptions import HashError
from ..hash import is_hash, to_hash
from ..interface import Repository
from ..ops import Conflict, gather, load_hash, save_hash
from ..utils import PathOrStr, deprecate
from .app import app_command
from .utils import normalize_sources_and_destination


@app_command
def add(
        sources: List[Path] = typer.Argument(..., help='The source paths to add', show_default=False),
        destination: Optional[Path] = typer.Option(
            None, '--destination', '--dst',
            help='The destination at which the hashes will be stored. '
                 'If none -  the hashes will be stored alongside the source'
        ),
        keep: bool = typer.Option(False, help='Whether to keep the sources after hashing'),
        conflict: Conflict = typer.Option(
            'error', case_sensitive=False, help=Conflict.__doc__.replace('\n\n', '\n').replace('\n', '\n\n')
        ),
        repository: Path = typer.Option(
            None, '--repository', '--repo', help='The bev repository. It is usually detected automatically',
            show_default=False,
        )
):
    """Add files and/or folders to a bev repository"""
    pairs, repo = normalize_sources_and_destination(sources, destination, repository)
    if not pairs:
        return

    for source, destination in pairs:
        if not is_hash(destination):
            destination = to_hash(destination)

        if source == destination:
            # TODO: warn
            continue

        _gather_and_write(source, destination, keep, conflict, repo.storage)


def _gather_and_write(source: PathOrStr, destination: PathOrStr, keep: bool, conflict: Conflict, storage):
    source, destination = Path(source), Path(destination)
    previous = None
    if destination.exists():
        if conflict == Conflict.error:
            raise HashError(f'The destination "{destination}" already exists and no conflict resolution provided')

        if not destination.is_file():
            raise HashError(f'The destination "{destination}" is not a file')

        if conflict != Conflict.replace:
            previous = load_hash(destination, storage)

    current = gather(source, storage, track)
    if previous is not None:
        if isinstance(current, dict):
            if not isinstance(previous, dict):
                raise HashError(f'The previous version ({destination}) is not a folder')

            if conflict == Conflict.update:
                for k in set(current) & set(previous):
                    if current[k] != previous[k]:
                        raise HashError(
                            f'The current ({current[k][:6]}...) and previous ({previous[k][:6]}...) '
                            f'versions do not match for "{k}", which is required for the "update" '
                            'conflict resolution'
                        )

            previous.update(current)
            current = previous

        else:
            if not isinstance(previous, str):
                raise HashError(f'The previous version ({destination}) is not a file')

            if conflict == Conflict.update and current != previous:
                raise HashError(
                    f'The current ({current[:6]}...) and previous ({previous[:6]}...) '
                    f'versions do not match, which is required for the "update" conflict resolution'
                )

    save_hash(current, destination, storage)

    if not keep:
        if source.is_dir():
            shutil.rmtree(source)
        else:
            os.remove(source)


@deprecate
def validate_file(path: Path):  # pragma: no cover
    assert path.is_file(), path
    if is_hash(path):
        raise ValueError('You are trying to add a hash to the storage.')

    return path


@deprecate
def save_tree(repo: Repository, tree: dict, destination: Path):  # pragma: no cover
    # save the directory description
    # making sure that each time the same string will be saved
    tree = OrderedDict((k, tree[k]) for k in sorted(tree))
    # FIXME
    tree_path = destination.parent / f'{destination.name}.hash.temp'

    # TODO: storage should allow writing directly from memory
    with open(tree_path, 'w') as file:
        json.dump(tree, file)
    key = repo.storage.write(tree_path).hex()
    os.remove(tree_path)

    with open(destination, 'w') as file:
        file.write(f'T:{key}')

    return key


@deprecate
def add_file(repo: Repository, source: Path, destination: Optional[Path], keep: bool):  # pragma: no cover
    validate_file(source)
    key = repo.storage.write(source).hex()

    if destination is not None:
        assert is_hash(destination)
        with open(destination, 'w') as file:
            file.write(key)

    if not keep:
        os.remove(source)

    return key


@deprecate
def add_folder(repo: Repository, source: Path, destination: Optional[Path], keep: bool):  # pragma: no cover
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
