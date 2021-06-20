from pathlib import Path

from bev.config import get_current_repo
from bev.interface import UNCOMMITTED


def test_glob(tests_root):
    repo = get_current_repo(tests_root / 'data')

    assert set(repo.glob('images/*.png', version=UNCOMMITTED)) == set(
        map(Path, ['images/1.png', 'images/2.png', 'images/3.png']))
