import os
import tempfile
from pathlib import Path

import pytest

from bev.cli.add import add
from connectome.storage.config import init_storage


@pytest.fixture(scope="session", autouse=True)
def setup_config():
    data_root = Path(__file__).parent / 'data'

    with tempfile.TemporaryDirectory() as storage:
        storage = Path(storage) / 'storage'

        # create config
        with open(data_root / '.bev.yml', 'w') as file:
            # language=YAML
            file.write('tests: {storage: [{root: %s}]}' % storage)

        init_storage(storage, algorithm={'name': 'blake2b', 'digest_size': 64}, levels=[1, 31, 32])
        add(data_root / 'images', data_root, True, data_root)
        yield
        os.remove(data_root / '.bev.yml')
        os.remove(data_root / 'images.hash')


@pytest.fixture
def tests_root():
    return Path(__file__).parent
