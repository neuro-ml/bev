import os
import shutil
from pathlib import Path

import pytest

from bev.cli.add import add_file

from bev import Local, Repository
from bev.exceptions import InconsistentHash
from bev.ops import save_hash
from bev.testing import create_structure


def test_glob(temp_repo):
    repo = Repository(temp_repo)
    images = ['images/1.png', 'images/2.png', 'images/3.png']
    create_structure(temp_repo, images)

    assert set(repo.glob('images/*.png', version=Local)) == set(map(Path, images))


def test_from_here(temp_repo_factory):
    root = Path(__file__).resolve().parent.parent / 'some-repo'
    root.mkdir()
    with temp_repo_factory(root):
        try:
            repo = Repository.from_here('../some-repo')
            assert repo.root.resolve() == root.resolve()
        finally:
            shutil.rmtree(root)


def test_class_defaults(temp_repo):
    repo = Repository(temp_repo, version=Local)
    save_hash({}, temp_repo / '4.png.hash', repo)
    repo.resolve('4.png')


def test_hash_consistency(temp_repo):
    temp_repo = Repository(temp_repo)
    add_file(temp_repo, Path(__file__), temp_repo.root / 'file.hash', True)

    # ok
    file = 'file'
    path = temp_repo.resolve(file, version=Local, check=True)
    # break the file
    os.chmod(path, 0o777)
    with open(path, 'w') as fd:
        fd.write('!')

    # still ok
    temp_repo.resolve(file, version=Local, check=False)
    # not ok
    with pytest.raises(InconsistentHash):
        temp_repo.resolve(file, version=Local, check=True)

    # default mode
    temp_repo = Repository(temp_repo.root, check=True)
    with pytest.raises(InconsistentHash):
        temp_repo.resolve(file, version=Local)
