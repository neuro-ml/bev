import os
import shutil
import warnings
from enum import Enum
from pathlib import Path
from typing import Optional, List

import typer
from tqdm.auto import tqdm

from .add import add
from .app import cli_error, _app, app_command
from .utils import normalize_sources, normalize_sources_and_destination
from ..exceptions import HashError
from ..hash import is_hash, to_hash, from_hash
from ..ops import load_hash, Conflict


class PullMode(Enum):
    copy = 'copy'
    hash = 'hash'


@app_command
def pull(
        sources: List[Path] = typer.Argument(..., help='The source paths to add', show_default=False),
        mode: PullMode = typer.Argument(..., help='Pull mode', show_default=False),
        destination: Optional[Path] = typer.Option(
            None, '--destination', '--dst',
            help='The destination at which the hashes will be stored. '
                 'If none -  the hashes will be stored alongside the source'
        ),
        keep: bool = typer.Option(False, help='Whether to keep the sources after hashing'),
        repository: Path = typer.Option(
            None, '--repository', '--repo', help='The bev repository. It is usually detected automatically',
            show_default=False,
        )
):
    """Restore the files and folders that were added to storage"""

    raw_sources = normalize_sources(sources)
    sources = []
    for source in raw_sources:
        if source.exists():
            if source.is_dir():
                for file in source.glob('**/*'):
                    if file.is_file() and is_hash(file):
                        sources.append(file)

            else:
                if not is_hash(source):
                    raise HashError(f'The source "{source}" is not a hash')

                sources.append(source)

        else:
            if not is_hash(source):
                source = to_hash(source)
            sources.append(source)

    pairs, repo = normalize_sources_and_destination(sources, destination, repository)
    if not pairs:
        return

    for source, destination in pairs:
        if is_hash(destination):
            destination = from_hash(destination)

        if source == destination:
            # TODO: warn
            continue

        _pull(source, destination, mode, keep, repo)


def _pull(source, destination, mode, keep, repo):
    h = load_hash(source, repo.storage)
    if isinstance(h, dict):
        if destination.is_file():
            raise cli_error(
                OSError,
                f'The destination ({destination}) is a file, but the hash ({source}) contains a folder',
            )

        for file, value in tqdm(h.items()):
            file = destination / file
            file.parent.mkdir(parents=True, exist_ok=True)
            PULL_MODES[mode](value, file, repo)

    else:
        if destination.is_dir():
            raise cli_error(
                OSError,
                f'The destination ({destination}) is a folder, but the hash ({source}) contains a single file',
            )

        PULL_MODES[mode](h, destination, repo)

    if not keep:
        os.remove(source)


def save_hash(value, file, repo):
    with open(to_hash(file), 'w') as f:
        f.write(value)


PULL_MODES = {
    'copy': lambda h, dst, repo: repo.storage.read(shutil.copyfile, h, dst),
    'hash': save_hash,
}


@_app.command(deprecated=True)
def gather(
        source: Path = typer.Argument(..., help='The source path to gather', show_default=False),
        destination: Optional[Path] = typer.Option(
            None, '--destination', '--dst',
            help='The destination at which the hashes will be stored. '
                 'If none -  the hashes will be stored alongside the source'
        ),
):  # pragma: no cover
    """Reverse a "pull" command. Warning! this command is superseded by "add" and will be removed soon"""

    warnings.warn('This command is deprecated. Use "add" instead', UserWarning)
    warnings.warn('This command is deprecated. Use "add" instead', DeprecationWarning)
    return add([source], destination, False, Conflict.error, '.')
