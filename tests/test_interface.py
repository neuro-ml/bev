from pathlib import Path

from bev import Local, Repository


def test_glob(data_root):
    repo = Repository(data_root)

    assert set(repo.glob('images/*.png', version=Local)) == set(
        map(Path, ['images/1.png', 'images/2.png', 'images/3.png']))
