import warnings
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from ..ops import Conflict
from .add import add
from .app import _app


@_app.command(deprecated=True)
def update(
        source: Path = typer.Argument(..., help='The source path to gather', show_default=False),
        destination: Annotated[Optional[Path], typer.Option(
            None, '--destination', '--dst',
            help='The destination at which the hashes will be stored. '
                 'If none -  the hashes will be stored alongside the source'
        )] = None,
        keep: Annotated[bool, typer.Option(False, help='Whether to keep the sources after hashing')] = False,
        overwrite: Annotated[bool, typer.Option(
            False, 
            help='Whether to overwrite the existing values in case of conflict'
        )] = False,
):  # pragma: no cover
    """Add new entries to a folder hash. Warning! this command is superseded by "add" and will be removed soon"""

    warnings.warn('This command is deprecated. Use "add" instead', UserWarning)
    warnings.warn('This command is deprecated. Use "add" instead', DeprecationWarning)
    return add([source], destination, keep, Conflict.override if overwrite else Conflict.update, '.')
