from pathlib import Path

from bev import Local, Repository


def test_glob(tests_root):
    repo = Repository.from_root(tests_root / 'data')

    assert set(repo.glob('images/*.png', version=Local)) == set(
        map(Path, ['images/1.png', 'images/2.png', 'images/3.png']))
