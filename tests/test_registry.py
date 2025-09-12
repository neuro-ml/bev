import pytest

from bev.config import LocationConfig, NginxConfig, RegistryError, find, register


def test_invalid():
    with pytest.raises(TypeError, match='is not a type'):
        register('ssh', 1)
    with pytest.raises(TypeError, match='match the type'):
        register('ssh', int)
    with pytest.raises(ValueError, match='reserved'):
        register('ssh', NginxConfig)


def test_find():
    with pytest.raises(RegistryError, match='not found'):
        find('ssh', int)
    with pytest.raises(RegistryError, match='Invalid key'):
        find('missing', LocationConfig)


def test_find_import():
    assert find('bev.config.location.NginxConfig', LocationConfig) == NginxConfig
