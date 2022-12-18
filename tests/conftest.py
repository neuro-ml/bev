import hashlib
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from tarn.config import init_storage, StorageConfig


@pytest.fixture
def tests_root():
    return Path(__file__).parent


@pytest.fixture
def configs_root(tests_root):
    return tests_root / 'configs'


@pytest.fixture
def temp_repo_factory():
    @contextmanager
    def factory(root=None):
        with tempfile.TemporaryDirectory() as storage, tempfile.TemporaryDirectory() as repo:
            storage = Path(storage) / 'storage'
            if root is not None:
                repo = root
            repo = Path(repo)

            # create config
            with open(repo / '.bev.yml', 'w') as file:
                # language=YAML
                file.write('tests: {storage: [{root: %s}]}' % storage)

            init_storage(StorageConfig(hash='sha256', levels=[1, 31]), storage)
            yield repo

    return factory


@pytest.fixture
def temp_repo(temp_repo_factory) -> Path:
    with temp_repo_factory() as repo:
        yield repo


@pytest.fixture
def sha256empty() -> str:
    return hashlib.sha256().hexdigest()


@pytest.fixture
def chdir():
    @contextmanager
    def manager(path):
        cwd = os.getcwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(cwd)

    return manager
