from io import StringIO
from unittest import mock

import pytest
from pydantic import ValidationError
from yaml import safe_load

from bev.config import CacheConfig, StorageCluster, StorageConfig, load_config, parse
from bev.config.location import (
    DiskDictConfig, FanoutConfig, LevelConfig, LevelsConfig, NginxConfig, SCPConfig, SFTPConfig
)
from bev.config.parse import _parse, _parse_entry
from bev.exceptions import ConfigError


@pytest.mark.parametrize('name', ['first', 'second', 'third'])
def test_select_name(name):
    config = {
        'first': {'storage': '1'},
        'second': {'storage': '2'},
        'meta': {'fallback': 'first'}
    }
    with mock.patch('socket.gethostname', return_value=name):
        config = parse('<string input>', config)
        if name == 'third':
            assert config.local.name == 'first'
        else:
            assert config.local.name == name
        assert len(config.remotes) == 1


# language=yaml
parameters = (
    ('''
c1:
  storage: '/a/b'
''', StorageCluster(name='c1', storage=StorageConfig(local=DiskDictConfig(root='/a/b')))), ('''
c2:
  storage:
    local: '/a/b'
    remote:
      nginx: 'https://example.com'
''', StorageCluster(name='c2', storage=StorageConfig(
        local=DiskDictConfig(root='/a/b'), remote=NginxConfig(url='https://example.com')))), ('''
c3:
  storage:
    local: '/a/b'
    remote:
      - nginx: 'https://example.com'
      - scp: 'some-hostname:/path'
''', StorageCluster(name='c3', storage=StorageConfig(
        local=DiskDictConfig(root='/a/b'),
        remote=FanoutConfig(locations=[
            NginxConfig(url='https://example.com'), SCPConfig(host='some-hostname', root='/path'),
        ])))), ('''
c4:
  storage:
    local: 
      - '/a/b'
      - '/d/e'
    remote:
      - nginx: 'https://example.com'
      - scp: 'some-hostname:/some/path'
''', StorageCluster(name='c4', storage=StorageConfig(
        local=FanoutConfig(locations=[
            DiskDictConfig(root='/a/b'), DiskDictConfig(root='/d/e'),
        ]),
        remote=FanoutConfig(locations=[
            NginxConfig(url='https://example.com'), SCPConfig(host='some-hostname', root='/some/path'),
        ])))), ('''
c5:
  storage: '/a/b'
  cache: '/c/d'
''', StorageCluster(
        name='c5', storage=StorageConfig(local=DiskDictConfig(root='/a/b')),
        cache=CacheConfig(
            index=StorageConfig(local=DiskDictConfig(root='/c/d')),
            storage=StorageConfig(local=DiskDictConfig(root='/a/b'))
        ),
    )), ('''
c6:
  storage: '/a/b'
  cache:
    index: '/c/d'
''', StorageCluster(
        name='c6', storage=StorageConfig(local=DiskDictConfig(root='/a/b')),
        cache=CacheConfig(
            index=StorageConfig(local=DiskDictConfig(root='/c/d')),
            storage=StorageConfig(local=DiskDictConfig(root='/a/b'))
        ),
    )), ('''
c7:
  storage: '/a/b'
  cache:
    index: '/c/d'
    storage: '/e/f'
''', StorageCluster(
        name='c7', storage=StorageConfig(local=DiskDictConfig(root='/a/b')),
        cache=CacheConfig(
            index=StorageConfig(local=DiskDictConfig(root='/c/d')),
            storage=StorageConfig(local=DiskDictConfig(root='/e/f'))
        ),
    )), ('''
c8:
  storage: 
    fanout:
      - '/a/b'
      - '/c/d'
''', StorageCluster(name='c8', storage=StorageConfig(
        local=FanoutConfig(locations=[
            DiskDictConfig(root='/a/b'), DiskDictConfig(root='/c/d'),
        ])))), ('''
c9:
  storage: 
    levels:
      - '/a/b'
''', StorageCluster(name='c9', storage=StorageConfig(
        local=LevelsConfig(levels=[
            LevelConfig(location=DiskDictConfig(root='/a/b'))
        ])))), ('''
c10:
  storage:
    local: '/a/b'
    remote:
      - nginx: 'https://example.com'
      - sftp: 'some-hostname:/path'
''', StorageCluster(name='c10', storage=StorageConfig(
        local=DiskDictConfig(root='/a/b'),
        remote=FanoutConfig(locations=[
            NginxConfig(url='https://example.com'), SFTPConfig(host='some-hostname', root='/path'),
        ]))))
)


@pytest.mark.parametrize('config,expected', parameters)
def test_storage_parser(config, expected):
    (name, config), = safe_load(StringIO(config)).items()
    assert _parse_entry(name, config) == expected


def test_parser(configs_root, subtests):
    for file in configs_root.glob('*.yml'):
        with subtests.test(config=file.name):
            with open(file, 'r') as fd:
                _parse(file, safe_load(fd), file)


def test_simplified(configs_root):
    assert load_config(configs_root / 'single-full.yml') == load_config(configs_root / 'single-simplified.yml')


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


def test_wrong_storage():
    # it used to raise KeyError
    with pytest.raises(ValidationError):
        parse('<string input>', {'a': {
            'storage': {'wrong-key': None},
            'cache': 'b'
        }})


def test_inheritance(configs_root):
    file = configs_root / 'compound.yml'
    with open(file, 'r') as fd:
        meta, config = _parse(file, safe_load(fd), file)

    assert set(config) == {'some-name-from-second', 'own-entry', 'child-entry'}
    assert meta.fallback == 'overridden-fallback'
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


def test_custom_cache_storage(configs_root):
    config = load_config(configs_root / 'custom-cache-storage.yml')
    assert config.local.cache.storage != config.local.storage

    config = load_config(configs_root / 'full.yml')
    assert config.local.cache.storage == config.local.storage
