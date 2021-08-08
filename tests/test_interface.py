from pathlib import Path

from bev import Local, Repository


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
