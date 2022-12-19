from typer.testing import CliRunner

from bev import Repository
from bev.cli.entrypoint import app
from bev.hash import tree_to_hash
from bev.testing import create_structure

runner = CliRunner()


def test_fetch(temp_repo, chdir):
    storage = Repository(temp_repo).storage
    file_hash = storage.write(__file__)
    create_structure(temp_repo, {
        'a.hash': file_hash,
        'b': None,
        'c.hash': tree_to_hash({
            'd': file_hash,
        }, storage),
    })

    with chdir(temp_repo):
        result = runner.invoke(app, ['fetch', 'a'])
        assert result.exit_code == 0, result.output
        result = runner.invoke(app, ['fetch', 'a.hash'])
        assert result.exit_code == 0, result.output
        result = runner.invoke(app, ['fetch', 'c'])
        assert result.exit_code == 0, result.output
        result = runner.invoke(app, ['fetch', 'b'])
        assert result.exit_code == 255
        assert result.output == 'HashError Cannot fetch "b" - it is not a hash nor a folder\n'
        result = runner.invoke(app, ['fetch', '.'])
        assert result.exit_code == 0, result.output
        result = runner.invoke(app, ['fetch'])
        assert result.exit_code == 0, result.output


def test_fetch_missing(temp_repo, sha256empty):
    create_structure(temp_repo, {
        'a.hash': sha256empty,
    })
    result = runner.invoke(app, ['fetch', str(temp_repo / 'a')])
    assert result.exit_code == 255
    assert 'HashNotFound Could not fetch 1 key(s) from remote\n' in result.output


def test_pull(temp_repo, chdir):
    structure = {
        'file.npy': 'first file content',
        'folder/a.txt': 'nested a content',
        'folder/b.bin': 'nested b content',
    }
    create_structure(temp_repo, structure)
    with chdir(temp_repo):
        result = runner.invoke(app, ['add', 'file.npy', 'folder'])
        assert result.exit_code == 0

        result = runner.invoke(app, ['pull', 'file.npy.hash', 'folder.hash', '--mode', 'copy'])
        assert result.exit_code == 0
        for file, content in structure.items():
            with open(file, 'r') as fd:
                assert fd.read() == content

# def test_init(tests_root, tmpdir):
#     tmpdir = Path(tmpdir)
#     _, group = root_params(tmpdir)
#     permissions = 0o770
#     folders = ['one', 'two', 'nested/folders', 'cache']
#
#     current = os.getcwd()
#     try:
#         os.chdir(tmpdir)
#         config = load_config(tests_root / 'assets' / 'to-init.yml')
#         init_config(config, permissions, group)
#
#         for folder in folders:
#             folder = Path(folder)
#
#             assert folder.exists()
#             assert (permissions, group) == root_params(folder)
#             assert (folder / 'config.yml').exists()
#             storage_config = load_storage_config(folder)
#             assert storage_config.hash == config.meta.hash
#             assert tuple(storage_config.levels) == (1, 31)
#
#     finally:
#         os.chdir(current)
