from bev.cli.fetch import fetch


def test_fetch(tests_root):
    fetch(['images.hash'], tests_root / 'data')
    fetch([tests_root / 'data' / 'images.hash'])
