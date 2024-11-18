import hashlib
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from tarn.config import StorageConfig, init_storage

from bev.cli.add import add
from bev.ops import Conflict
from bev.testing import create_structure


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
            make_repo(repo, storage)
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
    return _chdir


@pytest.fixture
def temp_dir(tmpdir):
    return Path(tmpdir)


@pytest.fixture(scope='session')
def git_repository():
    def freeze(tag):
        subprocess.call(['git', 'add', '.'], cwd=repo)
        subprocess.call(['git', 'commit', '-m', 'empty'], cwd=repo)
        subprocess.call(['git', 'tag', tag], cwd=repo)

    def bev_add(*files):
        add(files, None, False, Conflict.error, None)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        repo = tmp / 'repo'
        bev_repo = repo / 'bev-repo'
        bev_repo.mkdir(parents=True)
        make_repo(bev_repo, tmp / 'storage')

        with _chdir(bev_repo):
            # we don't want to mess up our personal config
            if 'CI' in os.environ:
                subprocess.call(['git', 'config', '--global', 'user.email', 'you@example.com'], cwd=repo)
                subprocess.call(['git', 'config', '--global', 'user.name', 'Name'], cwd=repo)

            subprocess.call(['git', 'init'], cwd=repo)
            create_structure(bev_repo, [
                'just-a-file.txt',
                'another.file',
                'images/one.png',
                'images/two.png',
                'folder/file.txt',
                'folder/nested/a.npy',
                'folder/nested/b.npy',
            ])
            freeze('v1')

            bev_add('another.file', 'folder/nested/a.npy')
            Path('folder/nested/c.npy').touch()
            freeze('v2')

            bev_add('folder/nested')
            os.remove('another.file.hash')
            freeze('v3')

            bev_add('folder')
            freeze('v4')

            Path('new-file.txt').touch()

            yield repo


# local assets
def make_repo(repo, storage):
    storage = Path(storage) / 'storage'
    repo = Path(repo)

    # create config
    with open(repo / '.bev.yml', 'w') as file:
        # language=YAML
        file.write('tests: {storage: %s}' % storage)

    init_storage(StorageConfig(hash='sha256', levels=[1, 31]), storage)


@contextmanager
def _chdir(path):
    cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)
