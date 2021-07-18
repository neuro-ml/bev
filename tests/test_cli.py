from bev.cli.fetch import fetch


def test_fetch(data_root):
    fetch(['images.hash'], data_root)
    fetch([data_root / 'images.hash'])
    fetch([data_root / '4.png.hash'])
