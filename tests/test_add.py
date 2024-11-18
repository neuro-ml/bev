from pathlib import Path

from typer.testing import CliRunner

from bev import Repository
from bev.cli.entrypoint import app
from bev.hash import is_tree, load_key, load_tree, strip_tree, tree_to_hash
from bev.testing import TempDir, create_structure


runner = CliRunner()


def test_add_relative(temp_repo_factory, temp_dir, chdir):
    temp_one, temp_two = temp_dir / 'one', temp_dir / 'two'
    with temp_repo_factory() as temp_repo_one, temp_repo_factory() as temp_repo_two:
        for root in temp_one, temp_two, temp_repo_one, temp_repo_two:
            create_structure(root, [
                'some-file.png',
                'nested/file.json',
                'nested/folder/a.npy',
                'nested/folder/b.jpeg',
                'folder/a',
                'folder/b',
            ])

        with chdir(temp_repo_one):
            # single file
            result = runner.invoke(app, ['add', 'some-file.png'])
            assert result.exit_code == 0, result.output
            assert not (temp_repo_one / 'some-file.png').exists()
            assert (temp_repo_one / 'some-file.png.hash').exists()

            # nested file
            result = runner.invoke(app, ['add', 'nested/file.json'])
            assert result.exit_code == 0
            assert not (temp_repo_one / 'nested/file.json').exists()
            assert (temp_repo_one / 'nested/file.json.hash').exists()

            # folder
            result = runner.invoke(app, ['add', 'folder'])
            assert result.exit_code == 0
            assert not (temp_repo_one / 'folder').exists()
            assert (temp_repo_one / 'folder.hash').exists()
            assert is_tree(load_key(temp_repo_one / 'folder.hash'))

            # nested folder
            result = runner.invoke(app, ['add', 'nested/folder'])
            assert result.exit_code == 0
            assert not (temp_repo_one / 'nested/folder').exists()
            assert (temp_repo_one / 'nested/folder.hash').exists()
            assert is_tree(load_key(temp_repo_one / 'nested/folder.hash'))

            # and the same from outside

            # single file
            result = runner.invoke(app, ['add', str(temp_one / 'some-file.png')])
            assert result.exit_code == 0, result.output
            assert not (temp_one / 'some-file.png').exists()
            assert (temp_one / 'some-file.png.hash').exists()

            # nested file
            result = runner.invoke(app, ['add', str(temp_one / 'nested/file.json')])
            assert result.exit_code == 0
            assert not (temp_one / 'nested/file.json').exists()
            assert (temp_one / 'nested/file.json.hash').exists()

            # folder
            result = runner.invoke(app, ['add', str(temp_one / 'folder')])
            assert result.exit_code == 0
            assert not (temp_one / 'folder').exists()
            assert (temp_one / 'folder.hash').exists()
            assert is_tree(load_key(temp_one / 'folder.hash'))

            # nested folder
            result = runner.invoke(app, ['add', str(temp_one / 'nested/folder')])
            assert result.exit_code == 0
            assert not (temp_one / 'nested/folder').exists()
            assert (temp_one / 'nested/folder.hash').exists()
            assert is_tree(load_key(temp_one / 'nested/folder.hash'))

        # now the same stuff from outside the repo
        result = runner.invoke(app, ['add', str(temp_repo_two / 'some-file.png')])
        assert result.exit_code == 0
        assert not (temp_repo_two / 'some-file.png').exists()
        assert (temp_repo_two / 'some-file.png.hash').exists()

        # nested file
        result = runner.invoke(app, ['add', str(temp_repo_two / 'nested/file.json')])
        assert result.exit_code == 0
        assert not (temp_repo_two / 'nested/file.json').exists()
        assert (temp_repo_two / 'nested/file.json.hash').exists()

        # folder
        result = runner.invoke(app, ['add', str(temp_repo_two / 'folder')])
        assert result.exit_code == 0
        assert not (temp_repo_two / 'folder').exists()
        assert (temp_repo_two / 'folder.hash').exists()
        assert is_tree(load_key(temp_repo_two / 'folder.hash'))

        # nested folder
        result = runner.invoke(app, ['add', str(temp_repo_two / 'nested/folder')])
        assert result.exit_code == 0
        assert not (temp_repo_two / 'nested/folder').exists()
        assert (temp_repo_two / 'nested/folder.hash').exists()
        assert is_tree(load_key(temp_repo_two / 'nested/folder.hash'))

        # and with explicit repo

        # single file
        result = runner.invoke(app, ['add', str(temp_two / 'some-file.png'), '--repository', str(temp_repo_one)])
        assert result.exit_code == 0
        assert not (temp_two / 'some-file.png').exists()
        assert (temp_two / 'some-file.png.hash').exists()

        # nested file
        result = runner.invoke(app, ['add', str(temp_two / 'nested/file.json'), '--repository', str(temp_repo_one)])
        assert result.exit_code == 0
        assert not (temp_two / 'nested/file.json').exists()
        assert (temp_two / 'nested/file.json.hash').exists()

        # folder
        result = runner.invoke(app, ['add', str(temp_two / 'folder'), '--repository', str(temp_repo_one)])
        assert result.exit_code == 0
        assert not (temp_two / 'folder').exists()
        assert (temp_two / 'folder.hash').exists()
        assert is_tree(load_key(temp_two / 'folder.hash'))

        # nested folder
        result = runner.invoke(app, ['add', str(temp_two / 'nested/folder'), '--repository', str(temp_repo_one)])
        assert result.exit_code == 0
        assert not (temp_two / 'nested/folder').exists()
        assert (temp_two / 'nested/folder.hash').exists()
        assert is_tree(load_key(temp_two / 'nested/folder.hash'))


def test_not_found():
    result = runner.invoke(app, ['add', '/tmp/missing/some/path'])
    assert result.exit_code == 255
    assert result.output == 'The source "/tmp/missing/some/path" does not exist\n'


def test_add_multiple(temp_repo, chdir):
    create_structure(temp_repo, [
        'a', 'b', 'c',
        'd', 'e', 'f',
        'g', 'h', 'i',
    ])

    with chdir(temp_repo):
        result = runner.invoke(app, ['add', 'a', 'b', 'c'])
        assert result.exit_code == 0
        assert all(not Path(x).exists() for x in ['a', 'b', 'c'])
        assert all(Path(x).with_suffix('.hash').exists() for x in ['a', 'b', 'c'])

        with TempDir() as tmp:
            result = runner.invoke(app, ['add', 'd', 'e', 'f', '--dst', str(tmp)])
            assert result.exit_code == 0
            assert all(not Path(x).exists() for x in ['d', 'e', 'f'])
            assert all(not Path(x).with_suffix('.hash').exists() for x in ['d', 'e', 'f'])
            assert all(Path(tmp, x).with_suffix('.hash').exists() for x in ['d', 'e', 'f'])

        result = runner.invoke(app, ['add', 'g', 'h', '--dst', 'i'])
        assert result.exit_code == 255, result.output
        assert result.output == 'HashError When using multiple sources the destination must be a folder\n'

        result = runner.invoke(app, ['add', 'g', 'h', '--dst', 'missing'])
        assert result.exit_code == 255, result.output
        assert result.output == 'HashError The destination folder does not exist\n'


def test_add_single_with_destination(temp_repo, chdir):
    create_structure(temp_repo, [
        'a', 'b/',
        'c', 'd',
        'e', 'f/',
    ])

    with chdir(temp_repo):
        result = runner.invoke(app, ['add', 'a', '--dst', 'b'])
        assert result.exit_code == 0
        assert not Path('a').exists()
        assert Path('b/a.hash').exists()

        result = runner.invoke(app, ['add', 'c', '--dst', 'missing/folder'])
        assert result.exit_code == 255
        assert result.output == 'The destination parent directory "missing" does not exist\n'

        result = runner.invoke(app, ['add', 'c', '--dst', 'd/folder'])
        assert result.exit_code == 255
        assert result.output == 'The destination parent "d" is not a directory\n'

        result = runner.invoke(app, ['add', 'e', '--dst', 'f/changed'])
        assert result.exit_code == 0
        assert not Path('e').exists()
        assert Path('f/changed.hash').exists()


def test_conflict(temp_repo, chdir, sha256empty):
    def read_tree(path):
        return storage.read(load_tree, strip_tree(load_key(path)))

    storage = Repository(temp_repo).storage
    wrong_hash = storage.write(__file__).hex()
    create_structure(temp_repo, {
        'a': None, 'b.hash': None, 'c.hash/': None,
        # files
        'r1': None, 'r2.hash': wrong_hash,
        'r3': None, 'r4.hash': wrong_hash,
        'r5': None, 'r6.hash': sha256empty,
        'r7': None, 'r8.hash': wrong_hash,
        'r9': None, 'r10.hash': tree_to_hash({
            'a': sha256empty,
        }, storage),
        # folders
        't1/a.json': None, 't2.hash': tree_to_hash({}, storage),
        't3/a.json': None, 't3/b.json': None, 't4.hash': tree_to_hash({
            'a.json': wrong_hash, 'c.json': wrong_hash,
        }, storage),
        't5/a.json': None, 't5/b.json': None, 't6.hash': tree_to_hash({
            'a.json': sha256empty, 'c.json': wrong_hash,
        }, storage),
        't7/a.json': None, 't7/b.json': None, 't8.hash': tree_to_hash({
            'a.json': wrong_hash, 'c.json': wrong_hash,
        }, storage),
        't9/a.json': None, 't10.hash': sha256empty,
    })

    with chdir(temp_repo):
        # error
        result = runner.invoke(app, ['add', 'a', '--dst', 'b'])
        assert result.exit_code == 255
        assert result.output.endswith(
            'HashError The destination "b.hash" already exists and no conflict resolution provided\n'
        )
        # not a file
        result = runner.invoke(app, ['add', 'a', '--dst', 'c', '--conflict', 'replace'])
        assert result.exit_code == 255
        assert result.output.endswith('HashError The destination "c.hash" is not a file\n')

        # replace file
        result = runner.invoke(app, ['add', 'r1', '--dst', 'r2', '--conflict', 'replace'])
        assert result.exit_code == 0
        assert not Path('r1').exists()
        assert load_key('r2.hash') == sha256empty
        # override file
        result = runner.invoke(app, ['add', 'r3', '--dst', 'r4', '--conflict', 'override'])
        assert result.exit_code == 0
        assert not Path('r3').exists()
        assert load_key('r4.hash') == sha256empty
        # update correct file
        result = runner.invoke(app, ['add', 'r5', '--dst', 'r6', '--conflict', 'update'])
        assert result.exit_code == 0
        assert not Path('r5').exists()
        assert load_key('r6.hash') == sha256empty
        # update wrong file
        result = runner.invoke(app, ['add', 'r7', '--dst', 'r8', '--conflict', 'update'])
        assert result.exit_code == 255
        assert result.output.endswith(
            f'HashError The current ({sha256empty[:6]}...) and previous ({wrong_hash[:6]}...) '
            'versions do not match, which is required for the "update" conflict resolution\n'
        )
        # wrong hash kind
        result = runner.invoke(app, ['add', 'r9', '--dst', 'r10', '--conflict', 'update'])
        assert result.exit_code == 255
        assert result.output.endswith(f'HashError The previous version (r10.hash) is not a file\n')

        # replace folder
        result = runner.invoke(app, ['add', 't1', '--dst', 't2', '--conflict', 'replace'])
        assert result.exit_code == 0
        assert not Path('t1').exists()
        assert read_tree('t2.hash') == {'a.json': sha256empty}
        # override folder
        result = runner.invoke(app, ['add', 't3', '--dst', 't4', '--conflict', 'override'])
        assert result.exit_code == 0
        assert not Path('t3').exists()
        assert read_tree('t4.hash') == {
            'a.json': sha256empty, 'b.json': sha256empty, 'c.json': wrong_hash,
        }
        # update correct folder
        result = runner.invoke(app, ['add', 't5', '--dst', 't6', '--conflict', 'update'])
        assert result.exit_code == 0
        assert not Path('t5').exists()
        assert read_tree('t6.hash') == {
            'a.json': sha256empty, 'b.json': sha256empty, 'c.json': wrong_hash,
        }
        # update wrong folder
        result = runner.invoke(app, ['add', 't7', '--dst', 't8', '--conflict', 'update'])
        assert result.exit_code == 255
        assert result.output.endswith(
            f'HashError The current ({sha256empty[:6]}...) and previous ({wrong_hash[:6]}...) '
            'versions do not match for "a.json", which is required for the "update" conflict resolution\n'
        )
        # wrong hash kind
        result = runner.invoke(app, ['add', 't9', '--dst', 't10', '--conflict', 'update'])
        assert result.exit_code == 255
        assert result.output.endswith(f'HashError The previous version (t10.hash) is not a folder\n')
