from unittest import mock

import pytest
from yaml import safe_load

from bev.config import parse, load_config
from bev.config.parse import _parse
from bev.exceptions import ConfigError


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


def test_parser(configs_root, subtests):
    for file in configs_root.glob('*.yml'):
        with subtests.test(config=file.name):
            with open(file, 'r') as fd:
                _parse(file, safe_load(fd), file)


def test_simplified(configs_root):
    assert load_config(configs_root / 'single-full.yml') == load_config(configs_root / 'single-simplified.yml')


def test_default(configs_root):
    config = load_config(configs_root / 'full.yml')
    default = config.local.default
    assert default == {'optional': True}
    for x in config.local.storage:
        assert x.default == default


def test_fallback():
    with pytest.raises(ConfigError, match='fallback'):
        parse('<string input>', {
            'meta': {'fallback': 'a'},
            'b': {'storage': '/'},
            'c': {'storage': '/'},
        })
    with pytest.raises(ConfigError, match='No matching entry'):
        parse('<string input>', {
            'b': {'storage': '/'},
            'c': {'storage': '/'},
        })


def test_inheritance(configs_root):
    file = configs_root / 'compound.yml'
    with open(file, 'r') as fd:
        meta, config = _parse(file, safe_load(fd), file)

    assert set(config) == {'some-name-from-second', 'own-entry', 'child-entry'}
    assert meta.fallback == 'overridden-fallback'
    assert meta.order == 'base-order'
    assert meta.choose is None


def test_inheritance_errors(configs_root):
    file = configs_root / 'errors/base.yml'
    with pytest.raises(ConfigError), open(file, 'r') as fd:
        _parse(file, safe_load(fd), file)


def test_custom_cache_storage(configs_root):
    config = load_config(configs_root / 'custom-cache-storage.yml')
    assert config.local.cache.storage != config.local.storage

    config = load_config(configs_root / 'full.yml')
    assert config.local.cache.storage == config.local.storage
