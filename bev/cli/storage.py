import hashlib
from enum import Enum
from pathlib import Path
from typing import List

import typer
from tarn.config import StorageConfig, init_storage
from typing_extensions import Annotated

from .app import app_command, cli_error


# because typer can't just accept a list of choices
def upd(d):
    for algo in sorted(hashlib.algorithms_guaranteed):
        d[algo] = algo


class Hashes(Enum):
    upd(locals())


@app_command
def storage(
        path: Annotated[Path, typer.Argument(help='The path to the storage root', show_default='The current directory')] = '.',
        hash: Annotated[Hashes, typer.Option(help='The hashing algorithm to use')] = 'sha256',
        levels: Annotated[List[int], typer.Option(
            help='The levels of folders nesting', show_default='1, digest_size - 1'
        )] = None,
        permissions: Annotated[str, typer.Option(
            '--permissions', '-p', help='The permissions mask used to create the storage, e.g. 770',
        )] = None,
        group: Annotated[str, typer.Option(
            '--group', '-g', help='The group used to create the storage',
        )] = None,
):
    """Create a storage at a given path"""

    if list(path.iterdir()):
        raise cli_error(FileExistsError, 'The folder is not empty')

    algo_name = hash.name
    algo = getattr(hashlib, algo_name)
    # try:
    #     params = {x.name: x.default for x in list(inspect.signature(algo).parameters.values())[1:]}
    # except ValueError:
    #     params = {}
    #
    # kwargs = {}
    # if params:
    #     all_params = '\n'.join(f'{k}: {v}' for k, v in kwargs.items())
    #     print(f'Default hash parameters:\n{all_params}\nModify hash parameters? (y/N): ', end='')
    #     if parse_yes():
    #         for param, default in params.items():
    #             print(f'Algorithm parameter "{param}" (Press Enter for {default}): ', end='')
    #             value = input().strip()
    #             if value:
    #                 value = ast.literal_eval(value)
    #                 if value != default:
    #                     kwargs[param] = value

    if levels is None:
        digest_size = algo().digest_size
        levels = 1, digest_size - 1

    init_storage(
        StorageConfig(hash=algo_name, levels=levels), path, permissions=permissions, group=group,
    )
