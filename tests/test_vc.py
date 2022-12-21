import subprocess
from contextlib import suppress

import pytest

from bev.vc import SubprocessGit, TreeEntry


def test_subprocess_git(temp_dir):
    subprocess.check_call(['git', 'init'], cwd=temp_dir)
    nested = temp_dir / 'folder/nested'
    nested.mkdir(parents=True)
    (nested / 'a').touch()
    (nested / 'b').touch()
    subprocess.check_call(['git', 'add', '.'], cwd=temp_dir)
    subprocess.check_call(['git', 'commit', '-m', 'empty'], cwd=temp_dir)
    subprocess.check_call(['git', 'tag', 'v1'], cwd=temp_dir)

    # same as git
    vc = SubprocessGit(temp_dir)
    assert vc.list_dir('.', 'v1') == [TreeEntry('folder', True, False)]
    assert vc.list_dir('folder', 'v1') == [TreeEntry('nested', True, False)]
    assert set(vc.list_dir('folder/nested', 'v1')) == {TreeEntry('a', False, False), TreeEntry('b', False, False)}
    with pytest.raises(FileNotFoundError):
        vc.list_dir('missing', 'v1')

    # nested
    vc = SubprocessGit(nested.parent)
    assert vc.list_dir('.', 'v1') == [TreeEntry('nested', True, False)]
    assert set(vc.list_dir('nested', 'v1')) == {TreeEntry('a', False, False), TreeEntry('b', False, False)}
    with pytest.raises(FileNotFoundError):
        vc.list_dir('missing', 'v1')

    # nested but with denormalized root
    vc = SubprocessGit(nested / '..')
    assert vc.list_dir('.', 'v1') == [TreeEntry('nested', True, False)]
    assert set(vc.list_dir('nested', 'v1')) == {TreeEntry('a', False, False), TreeEntry('b', False, False)}
    with pytest.raises(FileNotFoundError):
        vc.list_dir('missing', 'v1')


# @pytest.mark.xfail
# @pytest.mark.parametrize('version', [
#     '03b5b303e7a9e01e8023d2213cd53cccdca3b0c8',
#     '15fe35f04ff33467f1ffeaebe5c3f394da9db17a',
# ])
# def test_consistency(version, tests_root):
#     root = tests_root.parent / 'bev'
#     a, b = Dulwich(root), SubprocessGit(root)
#     for file in root.glob('**/*'):
#         if file.is_dir():
#             continue
#
#         relative = str(file.relative_to(root))
#         assert a.read(relative, version) == b.read(relative, version)
#         assert no_err(a, relative) == no_err(b, relative)


def no_err(repo, relative):
    with suppress(FileNotFoundError):
        return repo.get_version(relative)
