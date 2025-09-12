import os
import shutil
from pathlib import Path

import cloudpickle
import pytest
import tarn.pickler
from tarn.pickler.interface import PickleError

from bev import Local, Repository
from bev.exceptions import HashNotFound, InconsistentHash
from bev.testing import create_structure


def test_glob(git_repository):
    def check(version, expected, pattern=None):
        expected = set(map(Path, expected))
        # add folders
        if pattern is None:
            for entry in list(expected):
                expected.update(entry.parents)
            expected.discard(Path('.'))
            pattern = '**/*'
        assert set(repo.glob(pattern, version=version)) == expected

    repo = Repository(git_repository / 'bev-repo')
    # all content
    check('v1', [
        'just-a-file.txt',
        'another.file',
        'images/one.png',
        'images/two.png',
        'folder/file.txt',
        'folder/nested/a.npy',
        'folder/nested/b.npy',
    ])
    check('v2', [
        'just-a-file.txt',
        'another.file',
        'images/one.png',
        'images/two.png',
        'folder/file.txt',
        'folder/nested/a.npy',
        'folder/nested/b.npy',
        'folder/nested/c.npy',
    ])
    check('v3', [
        'just-a-file.txt',
        'images/one.png',
        'images/two.png',
        'folder/file.txt',
        'folder/nested/a.npy',
        'folder/nested/b.npy',
        'folder/nested/c.npy',
    ])
    check('v4', [
        'just-a-file.txt',
        'images/one.png',
        'images/two.png',
        'folder/file.txt',
        'folder/nested/a.npy',
        'folder/nested/b.npy',
        'folder/nested/c.npy',
    ])
    check(Local, [
        'just-a-file.txt',
        'images/one.png',
        'images/two.png',
        'folder/file.txt',
        'folder/nested/a.npy',
        'folder/nested/b.npy',
        'folder/nested/c.npy',
        'new-file.txt',
    ])

    # wildcards
    check('v4', [
        'folder/nested/',
    ], '*/*/')
    check('v4', [
        'just-a-file.txt',
        'folder/file.txt',
    ], '**/*.txt')
    check(Local, [
        'folder/nested/',
    ], '*/*/')
    check(Local, [
        'just-a-file.txt',
        'folder/file.txt',
        'new-file.txt',
    ], '**/*.txt')

    # now the same but with nesting
    repo = Repository(git_repository / 'bev-repo') / 'folder'
    # all content
    check('v1', [
        'file.txt',
        'nested/a.npy',
        'nested/b.npy',
    ])
    check('v2', [
        'file.txt',
        'nested/a.npy',
        'nested/b.npy',
        'nested/c.npy',
    ])
    check('v3', [
        'file.txt',
        'nested/a.npy',
        'nested/b.npy',
        'nested/c.npy',
    ])
    check('v4', [
        'file.txt',
        'nested/a.npy',
        'nested/b.npy',
        'nested/c.npy',
    ])
    check(Local, [
        'file.txt',
        'nested/a.npy',
        'nested/b.npy',
        'nested/c.npy',
    ])
    # wildcards
    check('v4', [
        'nested/',
    ], '*/')
    check('v4', [
        'file.txt',
    ], '**/*.txt')
    check(Local, [
        'nested/',
    ], '*/')
    check(Local, [
        'file.txt',
    ], '**/*.txt')


def test_resolve(git_repository):
    repo = Repository(git_repository / 'bev-repo')
    storage = repo.storage._local.root
    for local in [
        'just-a-file.txt',
        'images/one.png',
        'images/two.png',
        'new-file.txt',
        'images',
    ]:
        assert is_relative_to(repo.resolve(local, version=Local), git_repository)

    for local in [
        'folder/file.txt',
        'folder/nested/a.npy',
        'folder/nested/b.npy',
        'folder/nested/c.npy',
    ]:
        is_relative_to(repo.resolve(local, version=Local), storage)

    for local in [
        'folder',
        'folder/nested',
    ]:
        with pytest.raises(HashNotFound):
            repo.resolve(local, version=Local)

    for local in [
        'another.file',
        'folder/nested/a.npy',
    ]:
        assert is_relative_to(repo.resolve(local, version='v2'), storage)

    with pytest.raises(HashNotFound):
        repo.resolve('folder/nested', version='v3')


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
    create_structure(temp_repo, {'4.png.hash': repo.storage.write(__file__).hex()})
    repo.resolve('4.png')


def test_hash_consistency(temp_repo):
    temp_repo = Repository(temp_repo)
    create_structure(temp_repo.root, {'file.hash': temp_repo.storage.write(__file__).hex()})

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


def is_relative_to(this, *other):
    # copied from pathlib, for <py3.9 support
    try:
        this.relative_to(*other)
        return True
    except ValueError:
        return False


def test_pickleable_local():
    assert cloudpickle.loads(cloudpickle.dumps(Local)) == Local
    with pytest.raises(PickleError):
        tarn.pickler.dumps(Local)
