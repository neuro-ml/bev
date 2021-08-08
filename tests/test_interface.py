from pathlib import Path

from bev import Local, Repository


def test_glob(data_root):
    repo = Repository(data_root)

    assert set(repo.glob('images/*.png', version=Local)) == set(
        map(Path, ['images/1.png', 'images/2.png', 'images/3.png']))


def test_from_here():
    repo = Repository.from_here('data')
    assert repo.root.resolve() == Path('data').resolve()
