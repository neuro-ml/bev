import pytest

from bev import Repository
from bev.hash import tree_to_hash
from bev.ops import gather
from bev.testing import create_structure


def test_gather(tmpdir, temp_repo, tests_root, sha256empty):
    storage = Repository(temp_repo).storage
    hash_a = storage.write(tests_root / 'conftest.py').hex()
    hash_b = storage.write(tests_root / 'requirements.txt').hex()
    hash_c = storage.write(tests_root / 'test_ops.py').hex()
    entries = {
        'images/one.png': None,
        'images/two.png.hash': hash_a,
        'images/three.png.hash': hash_b,
        'images/nested/one.jpg': None,
        'images/nested/empty/': None,
        'images/nested/tree.hash': tree_to_hash({
            'inside/data.npy.gz': hash_a,
            'top.dcm': hash_c,
        }, storage),
        'one.txt': None,
        'two.npy.hash': hash_c,
        'root_tree.hash': tree_to_hash({
            'more.data.npy': hash_b,
        }, storage),
    }
    target = {
        'images/one.png': None,
        'images/two.png': hash_a,
        'images/three.png': hash_b,
        'images/nested/one.jpg': None,
        'images/nested/tree/inside/data.npy.gz': hash_a,
        'images/nested/tree/top.dcm': hash_c,
        'one.txt': None,
        'two.npy': hash_c,
        'root_tree/more.data.npy': hash_b,
    }

    tmpdir = create_structure(tmpdir, entries)
    tree = gather(tmpdir, storage)
    assert isinstance(tree, dict)
    assert set(tree) == set(target)
    for k, v in target.items():
        if v is not None:
            assert tree[k] == v, k

    assert gather(tmpdir / 'one.txt', storage) == sha256empty
    assert gather(tmpdir / 'two.npy.hash', storage) == hash_c
    assert gather(tmpdir / 'images/nested/tree.hash', storage) == {
        'inside/data.npy.gz': hash_a,
        'top.dcm': hash_c,
    }


def test_gather_nested_hash(tmpdir, temp_repo, tests_root, sha256empty):
    storage = Repository(temp_repo).storage
    tmpdir = create_structure(tmpdir, {
        'a.json': None,
        'b.hash': tree_to_hash({
            'c.txt': sha256empty,
        }, storage),
        'd.png.hash': sha256empty,
    })

    assert gather(tmpdir, storage) == {
        'a.json': sha256empty,
        'b/c.txt': sha256empty,
        'd.png': sha256empty,
    }


def test_gather_missing():
    with pytest.raises(FileNotFoundError):
        gather('/tmp/missing', None)
