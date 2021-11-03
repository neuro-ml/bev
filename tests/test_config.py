from unittest import mock

import pytest

from bev.config import parse


@pytest.mark.parametrize('name', ['first', 'second'])
def test_select_name(name):
    config = {'first': {'storage': [{'root': '1'}]}, 'second': {'storage': [{'root': '2'}]}}
    with mock.patch('socket.gethostname', return_value=name):
        config = parse('<string input>', config)
        assert config.local.name == name
        assert len(config.remotes) == 1
