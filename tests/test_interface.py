import os
from pathlib import Path

import pytest

from bev.cli.add import add_file

from bev import Local, Repository
from bev.exceptions import InconsistentHash


def test_glob(data_root):
    repo = Repository(data_root)

    assert set(repo.glob('images/*.png', version=Local)) == set(
        map(Path, ['images/1.png', 'images/2.png', 'images/3.png']))


def test_from_here():
    repo = Repository.from_here('data')
    expected = Path(__file__).parent / 'data'
    assert str(repo.root.resolve()) == str(expected.resolve())


def test_class_defaults(data_root):
    repo = Repository(data_root, version=Local)
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
