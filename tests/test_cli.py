import os
from pathlib import Path

import pytest

from bev.cli.add import add
from bev.cli.fetch import fetch
from bev.cli.init import init_config
from bev.config import load_config
from tarn.config import root_params, load_config as load_storage_config


def test_fetch(data_root):
    fetch(['images.hash'], data_root)
    fetch([data_root / 'images.hash'])
    fetch([data_root / '4.png.hash'])


def test_add(temp_repo_factory, data_root, tests_root):
    with pytest.raises(FileNotFoundError):
        add('non-existent-file', data_root, False)

    with pytest.raises(FileNotFoundError):
        add(data_root / '4.png', '/missing/nested/path/', False)

    with pytest.raises(FileNotFoundError):
        add([data_root / '4.png', data_root / 'images/1.png'], '/missing/nested/path/', False)

    # add multiple files to a single to file
    with pytest.raises(ValueError):
        add([data_root / '4.png', data_root / 'images/1.png'], __file__, False)

    with temp_repo_factory() as repo:
        # just add multiple files
        add([tests_root / 'conftest.py', tests_root / 'test_cli.py'], repo, True)
        assert (repo / 'conftest.py.hash').exists()
        assert (repo / 'test_cli.py.hash').exists()


def test_init(tests_root, tmpdir):
    tmpdir = Path(tmpdir)
    _, group = root_params(tmpdir)
    permissions = 0o770
    folders = ['one', 'two', 'nested/folders', 'cache']

    current = os.getcwd()
    try:
        os.chdir(tmpdir)
        config = load_config(tests_root / 'assets' / 'to-init.yml')
        init_config(config, permissions, group)

        for folder in folders:
            folder = Path(folder)

            assert folder.exists()
            assert (permissions, group) == root_params(folder)
            assert (folder / 'config.yml').exists()
            storage_config = load_storage_config(folder)
            assert storage_config.hash == config.meta.hash
            assert tuple(storage_config.levels) == (1, 31)

    finally:
        os.chdir(current)
