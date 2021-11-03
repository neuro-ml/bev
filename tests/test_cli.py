import pytest

from bev.cli.add import add
from bev.cli.fetch import fetch


def test_fetch(data_root):
    fetch(['images.hash'], data_root)
    fetch([data_root / 'images.hash'])
    fetch([data_root / '4.png.hash'])


def test_add(data_root):
    with pytest.raises(FileNotFoundError):
        add('non-existent-file', data_root, False)
