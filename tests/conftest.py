import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from bev.cli.add import add
from tarn.config import init_storage, StorageConfig


@pytest.fixture(scope="session", autouse=True)
def setup_config():
    data_root = Path(__file__).parent / 'data'

    with tempfile.TemporaryDirectory() as storage:
        storage = Path(storage) / 'storage'

        # create config
        with open(data_root / '.bev.yml', 'w') as file:
            # language=YAML
            file.write('tests: {storage: [{root: %s}]}' % storage)

        init_storage(StorageConfig(hash='blake2b', levels=[1, 63]), storage)
        add(data_root / 'images', data_root, True, data_root)
        add(data_root / '4.png', data_root, True, data_root)
        yield
        os.remove(data_root / '.bev.yml')
        os.remove(data_root / 'images.hash')
        os.remove(data_root / '4.png.hash')


@pytest.fixture
def tests_root():
    return Path(__file__).parent


@pytest.fixture
def data_root(tests_root):
    return tests_root / 'data'


@pytest.fixture
def temp_repo_factory():
    @contextmanager
    def factory():
        with tempfile.TemporaryDirectory() as storage, tempfile.TemporaryDirectory() as repo:
            storage = Path(storage) / 'storage'
            repo = Path(repo)

            # create config
            with open(repo / '.bev.yml', 'w') as file:
                # language=YAML
                file.write('tests: {storage: [{root: %s}]}' % storage)

            init_storage(StorageConfig(hash='blake2b', levels=[1, 63]), storage)
            yield repo

    return factory


@pytest.fixture
def temp_repo(temp_repo_factory) -> Path:
    with temp_repo_factory() as repo:
        yield repo
