import os
import tempfile
from pathlib import Path

import pytest

from bev.cli.add import add


@pytest.fixture(scope="session", autouse=True)
def setup_config():
    data_root = Path(__file__).parent / 'data'

    with tempfile.TemporaryDirectory() as storage:
        # create config
        with open(data_root / '.bev.yml', 'w') as file:
            # language=YAML
            file.write('tests: {storage: [{root: %s}]}' % storage)

        add(data_root / 'images', data_root, True, data_root)
        yield
        os.remove(data_root / '.bev.yml')
        os.remove(data_root / 'images.hash')


@pytest.fixture
def tests_root():
    return Path(__file__).parent
