# used to trigger commands indexing
from . import add, blame, fetch, init, pull, storage  # noqa
from .app import _app as app


def entrypoint():
    app()
