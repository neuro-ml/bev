import os
from pathlib import Path

from ..exceptions import HashError
from ..shortcuts import get_consistent_repo
from .app import cli_error


def normalize_sources(sources):
    if isinstance(sources, (str, os.PathLike)):
        sources = [Path(sources)]
    else:
        sources = list(map(Path, sources))

    return sources


def normalize_sources_and_destination(sources, destination, repository):
    sources = normalize_sources(sources)

    # an annoying special case
    if not sources:
        return [], None

    if repository is None:
        repository = '.'

    # gather the potential repositories root
    sources_root = []
    for source in sources:
        if not source.exists():
            raise cli_error(FileNotFoundError, f'The source "{source}" does not exist')
        sources_root.append(source.parent)

    # if the destination is empty - it's the same as the source + '.hash'
    if destination is None:
        pairs = [(x, x) for x in sources]
        repo = get_consistent_repo([repository, *sources_root])

    # or let the user decide
    else:
        destination = Path(destination)
        if len(sources) > 1:
            if not destination.exists():
                raise HashError('The destination folder does not exist')
            if not destination.is_dir():
                raise HashError('When using multiple sources the destination must be a folder')
            dst_root = destination
            pairs = [(x, destination / x.name) for x in sources]

        else:
            source, = sources

            if destination.exists():
                if destination.is_dir():
                    dst_root = destination
                    dst = destination / source.name
                else:
                    dst_root = destination.parent
                    dst = destination
            else:
                if not destination.parent.exists():
                    raise cli_error(
                        FileNotFoundError,
                        f'The destination parent directory "{destination.parent}" does not exist'
                    )
                if not destination.parent.is_dir():
                    raise cli_error(
                        FileNotFoundError,
                        f'The destination parent "{destination.parent}" is not a directory'
                    )

                dst_root = destination.parent
                dst = destination

            pairs = [(source, dst)]

        repo = get_consistent_repo([repository, dst_root, *sources_root])

    return pairs, repo
