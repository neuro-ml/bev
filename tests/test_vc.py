from contextlib import suppress

import pytest

from bev.vc import Dulwich, SubprocessGit


@pytest.mark.xfail
@pytest.mark.parametrize('version', [
    '03b5b303e7a9e01e8023d2213cd53cccdca3b0c8',
    '15fe35f04ff33467f1ffeaebe5c3f394da9db17a',
])
def test_consistency(version, tests_root):
    root = tests_root.parent / 'bev'
    a, b = Dulwich(root), SubprocessGit(root)
    for file in root.glob('**/*'):
        if file.is_dir():
            continue

        relative = str(file.relative_to(root))
        assert a.show(relative, version) == b.show(relative, version)
        assert no_err(a, relative) == no_err(b, relative)


def no_err(repo, relative):
    with suppress(FileNotFoundError):
        return repo.log(relative)
