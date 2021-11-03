from unittest import mock

import pytest

from bev.config import parse


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
