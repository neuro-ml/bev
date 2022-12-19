from pathlib import Path

import typer
import yaml
from tarn.config import CONFIG_NAME as STORAGE_CONFIG_NAME, root_params, StorageConfig
from tarn.utils import mkdir

from .app import app_command
from ..config import find_repo_root, CONFIG, load_config
from ..utils import RepositoryNotFound


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
    root = find_repo_root(repository)
    if root is None:
        raise RepositoryNotFound(f'{CONFIG} files not found in current folder\'s parents')

    return init_config(load_config(root / CONFIG), permissions, group)


def init_config(config, permissions, group):
    local, meta = config.local, config.meta
    if meta.hash is None:
        raise ValueError('The config\'s `meta` must contain a `hash` key')

    levels = list(local.storage)
    if local.cache is not None:
        levels.extend(local.cache.index)
        levels.extend(local.cache.storage)

    permissions, group = get_root_params(levels, permissions, group)

    for level in levels:
        for location in level.locations:
            storage_root = location.root
            if not storage_root.exists():
                mkdir(storage_root, permissions, group, parents=True)

            conf_path = storage_root / STORAGE_CONFIG_NAME
            if not conf_path.exists():
                with open(conf_path, 'w') as file:
                    yaml.safe_dump(StorageConfig(hash=meta.hash).dict(exclude_defaults=True), file)


def get_root_params(levels, permissions, group):
    for level in levels:
        for entry in level.locations:
            if entry.root.exists():
                return root_params(entry.root)

    if permissions is None:
        print('Could not infer the permissions, please specify them explicitly with the "--permissions" option')
        raise typer.Exit(255)
    if not set(permissions) <= set(map(str, range(8))):
        print(f'Wrong permissions mask format {permissions}')
        raise typer.Exit(255)

    permissions = int(permissions, base=8)
    if not 0 <= permissions <= 0o777:
        print(f'The permissions must be between 000 and 777, {permissions} provided')
        raise typer.Exit(255)

    if group is None:
        print('Could not infer the group, please specify it explicitly with the "--group" option')
        raise typer.Exit(255)
    return permissions, group
