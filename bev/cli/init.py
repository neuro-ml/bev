from pathlib import Path

import typer
from typing_extensions import Annotated

from ..config import CONFIG, load_config
from ..shortcuts import get_consistent_repo_root
from .app import app_command


@app_command
def init(
        repository: Annotated[Path, typer.Option(
            '--repository', '--repo', help='The bev repository. It is usually detected automatically',
            show_default=False,
        )] = None,
        permissions: Annotated[str, typer.Option(
            '--permissions', '-p', help='The permissions mask used to create the storage, e.g. 770',
        )] = None,
        group: Annotated[str, typer.Option(
            '--group', '-g', help='The group used to create the storage',
        )] = None,
):
    """Initialize a bev repository by creating the storage locations specified in its config"""
    if repository is None:
        repository = '.'
    root = get_consistent_repo_root([repository])
    return init_config(load_config(root / CONFIG), permissions, group)


def init_config(config, permissions, group):
    local, meta = config.local, config.meta
    if meta.hash is None:
        raise ValueError("The config's `meta` must contain a `hash` key")

    if permissions is not None:
        if isinstance(permissions, str):
            if not set(permissions) <= set(map(str, range(8))):
                print(f'Wrong permissions mask format {permissions}')
                raise typer.Exit(255)

            permissions = int(permissions, base=8)

        if not 0 <= permissions <= 0o777:
            print(f'The permissions must be between 000 and 777, {oct(permissions)} provided')
            raise typer.Exit(255)

    local.storage.local.init(meta, permissions, group)
    if local.cache is not None:
        local.cache.storage.local.init(meta, permissions, group)
        local.cache.index.local.init(meta, permissions, group)
