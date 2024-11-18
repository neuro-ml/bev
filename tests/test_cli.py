import grp
import os
import shutil
from pathlib import Path

import pytest
from tarn.config import load_config as load_storage_config, root_params
from typer.testing import CliRunner

from bev import Repository
from bev.cli.entrypoint import app
from bev.config import load_config
from bev.hash import to_hash, tree_to_hash
from bev.testing import TempDir, create_structure


runner = CliRunner()


def test_fetch(temp_repo, chdir):
    storage = Repository(temp_repo).storage
    file_hash = storage.write(__file__).hex()
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


@pytest.mark.parametrize('mode', ['copy', 'hash'])
def test_pull(temp_repo, chdir, mode):
    structure = {
        'file.npy': 'first file content',
        'folder/a.txt': 'nested a content',
        'folder/b.bin': 'nested b content',
    }
    create_structure(temp_repo, structure)
    with chdir(temp_repo):
        result = runner.invoke(app, ['add', 'file.npy', 'folder'])
        assert result.exit_code == 0

        result = runner.invoke(app, ['pull', 'file.npy.hash', 'folder.hash', '--mode', mode])
        assert result.exit_code == 0, result.output
        for file, content in structure.items():
            if mode == 'copy':
                assert not to_hash(file).exists()
                with open(file, 'r') as fd:
                    assert fd.read() == content
            elif mode == 'hash':
                assert not Path(file).exists(), list(temp_repo.iterdir())
                if '/' in file:
                    assert to_hash(file).exists(), list(temp_repo.iterdir())
                else:
                    assert to_hash(file).exists(), list(temp_repo.iterdir())
                with open(to_hash(file), 'r') as fd:
                    assert len(fd.read()) == 64

        result = runner.invoke(app, ['add', 'file.npy.hash' if mode == 'hash' else 'file.npy', 'folder'])
        assert result.exit_code == 0, result.output
        assert {x.name for x in temp_repo.iterdir()} == {'.bev.yml', 'file.npy.hash', 'folder.hash'}


def test_init(tests_root, chdir):
    folders = ['one', 'two', 'nested/folders', 'cache']

    def clear_storage():
        for f in list(storage.iterdir()):
            shutil.rmtree(f)

    with TempDir() as storage, TempDir() as repo:
        config_path = repo / '.bev.yml'
        with open(config_path, 'w') as fd:
            fd.write(
                # language=yaml
                '''
main:
  storage:
    - '{0}/one'
    - '{0}/two'
    - '{0}/nested/folders'

  cache:
    - '{0}/cache'

meta:
  hash: sha256
        '''.format(storage))
        config = load_config(config_path)

        result = runner.invoke(app, ['init'])
        assert result.exit_code == 255
        assert result.output == 'RepositoryNotFound .bev.yml files not found among folder\'s parents\n'

        result = runner.invoke(app, ['init', '--repo', str(repo)])
        assert result.exit_code == 0

        for folder in folders:
            folder = storage / folder

            assert folder.exists()
            assert (folder / 'config.yml').exists()
            storage_config = load_storage_config(folder)
            assert storage_config.hash == config.meta.hash
            assert tuple(storage_config.levels) == (1, 31)

        clear_storage()
        group_id = sorted(os.getgroups())[0]
        group = grp.getgrgid(group_id).gr_name
        result = runner.invoke(app, ['init', '--repo', str(repo), '--permissions', '770', '--group', group])
        assert result.exit_code == 0

        for folder in folders:
            folder = storage / folder

            assert folder.exists()
            assert (folder / 'config.yml').exists()
            assert (0o770, group_id) == root_params(folder)
            storage_config = load_storage_config(folder)
            assert storage_config.hash == config.meta.hash
            assert tuple(storage_config.levels) == (1, 31)

        clear_storage()
        with chdir(repo):
            result = runner.invoke(app, ['init'])
            assert result.exit_code == 0

            for folder in folders:
                folder = storage / folder

                assert folder.exists()
                assert (folder / 'config.yml').exists()
                storage_config = load_storage_config(folder)
                assert storage_config.hash == config.meta.hash
                assert tuple(storage_config.levels) == (1, 31)
