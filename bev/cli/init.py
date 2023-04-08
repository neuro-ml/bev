from pathlib import Path

import typer
import yaml
from tarn.config import CONFIG_NAME as STORAGE_CONFIG_NAME, StorageConfig
from tarn.utils import mkdir

from ..config import CONFIG, load_config
from ..shortcuts import get_consistent_repo_root
from .app import app_command


@app_command
def init(
        repository: Path = typer.Option(
            None, '--repository', '--repo', help='The bev repository. It is usually detected automatically',
            show_default=False,
        ),
        permissions: str = typer.Option(
            None, '--permissions', '-p', help='The permissions mask used to create the storage, e.g. 770',
        ),
        group: str = typer.Option(
            None, '--group', '-g', help='The group used to create the storage',
        ),
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

    levels = list(local.storage)
    if local.cache is not None:
        levels.extend(local.cache.index)
        levels.extend(local.cache.storage)

    if permissions is not None:
        if isinstance(permissions, str):
            if not set(permissions) <= set(map(str, range(8))):
                print(f'Wrong permissions mask format {permissions}')
                raise typer.Exit(255)

            permissions = int(permissions, base=8)

        if not 0 <= permissions <= 0o777:
            print(f'The permissions must be between 000 and 777, {oct(permissions)} provided')
            raise typer.Exit(255)

    for level in levels:
        for location in level.locations:
            storage_root = location.root
            if not storage_root.exists():
                mkdir(storage_root, permissions, group, parents=True)

            conf_path = storage_root / STORAGE_CONFIG_NAME
            if not conf_path.exists():
                with open(conf_path, 'w') as file:
                    yaml.safe_dump(StorageConfig(hash=meta.hash).dict(exclude_defaults=True), file)
