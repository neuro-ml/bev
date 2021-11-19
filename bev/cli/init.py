from typing import Union

import yaml

from bev.config import find_repo_root, CONFIG, load_config
from bev.utils import RepositoryNotFound
from connectome.storage.config import DiskConfig, STORAGE_CONFIG_NAME, root_params
from connectome.storage.utils import mkdir


def init(repository: str = '.', permissions: str = None, group: Union[int, str] = None):
    root = find_repo_root(repository)
    if root is None:
        raise RepositoryNotFound(f'{CONFIG} files not found in current folder\'s parents')

    return init_config(load_config(root / CONFIG), permissions, group)


def init_config(config, permissions, group):
    local, meta = config.local, config.meta
    digest_size = meta.hash.build()().digest_size
    permissions, group = get_root_params(local.storage + local.cache, permissions, group)

    for location in local.storage + local.cache:
        storage_root = location.root
        if not storage_root.exists():
            mkdir(storage_root, permissions, group, parents=True)

        conf_path = storage_root / STORAGE_CONFIG_NAME
        if not conf_path.exists():
            with open(conf_path, 'w') as file:
                yaml.safe_dump(DiskConfig(
                    hash=meta.hash, levels=[1, digest_size - 1]
                ).dict(exclude_defaults=True), file)


def get_root_params(entries, permissions, group):
    for entry in entries:
        if entry.root.exists():
            return root_params(entry.root)

    if permissions is None:
        permissions = input('Folder permissions:')
    if isinstance(permissions, str):
        permissions = int(permissions, base=8)
    assert 0 <= permissions <= 0o777
    if group is None:
        group = input('Folder group:')
    return permissions, group
