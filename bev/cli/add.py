import os
import shutil
from pathlib import Path
from typing import List, Optional

import typer
from rich.progress import track
from typing_extensions import Annotated

from ..exceptions import HashError
from ..hash import is_hash, to_hash
from ..ops import Conflict, gather, load_hash, save_hash
from ..utils import PathOrStr
from .app import app_command
from .utils import normalize_sources_and_destination


@app_command
def add(
        sources: Annotated[List[Path], typer.Argument(help='The source paths to add', show_default=False)],
        destination: Annotated[Optional[Path], typer.Option(
            '--destination', '--dst',
            help='The destination at which the hashes will be stored. '
                 'If none -  the hashes will be stored alongside the source'
        )] = None,
        keep: Annotated[bool, typer.Option(help='Whether to keep the sources after hashing')] = False,
        conflict: Annotated[Conflict, typer.Option(
            case_sensitive=False, help=Conflict.__doc__.replace('\n\n', '\n').replace('\n', '\n\n')
        )] = 'error',
        repository: Annotated[Path, typer.Option(
            '--repository', '--repo', help='The bev repository. It is usually detected automatically',
            show_default=False,
        )] = None
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
