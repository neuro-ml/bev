import pytest

from bev.config import register, HTTPRemote, find, RemoteConfig


def test_invalid():
    with pytest.raises(TypeError, match='is not a type'):
        register('ssh', 1)
    with pytest.raises(TypeError, match='match the type'):
        register('ssh', int)
    with pytest.raises(ValueError, match='reserved'):
        register('ssh', HTTPRemote)


def test_find():
    with pytest.raises(ValueError, match='not found'):
        find(int, 'ssh')
    with pytest.raises(ValueError, match='Invalid key'):
        find(RemoteConfig, 'missing')
