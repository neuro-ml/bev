from unittest import mock

import pytest
from ruamel_yaml import safe_load

from bev.config import parse, load_config
from bev.config.parse import _parse


@pytest.mark.parametrize('name', ['first', 'second', 'third'])
def test_select_name(name):
    config = {
        'first': {'storage': [{'root': '1'}]},
        'second': {'storage': [{'root': '2'}]},
        'meta': {'fallback': 'first'}
    }
    with mock.patch('socket.gethostname', return_value=name):
        config = parse('<string input>', config)
        if name == 'third':
            assert config.local.name == 'first'
        else:
            assert config.local.name == name
        assert len(config.remotes) == 1


def test_parser(tests_root, subtests):
    for file in tests_root.glob('configs/**/*.yml'):
        with subtests.test(config=file.name):
            with open(file, 'r') as fd:
                _parse(file, safe_load(fd), file)


def test_simplified(tests_root):
    assert load_config(tests_root / 'configs/single-full.yml') == load_config(
        tests_root / 'configs/single-simplified.yml')


def test_default(tests_root):
    config = load_config(tests_root / 'configs/full.yml')
    default = config.local.default
    assert default == {'optional': True}
    for x in config.local.storage:
        assert x.default == default


def test_inheritance(tests_root):
    file = tests_root / 'configs/compound.yml'
    with open(file, 'r') as fd:
        meta, config = _parse(file, safe_load(fd), file)

    assert set(config) == {'some-name-from-second', 'own-entry', 'child-entry'}
