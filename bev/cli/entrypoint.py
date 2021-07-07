from argparse import ArgumentParser

from .add import add
from .blame import blame
from .fetch import fetch
from .pull import pull, gather, PULL_MODES
from .storage import init_storage
from .update import update


def entrypoint():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    new = subparsers.add_parser('add')
    new.set_defaults(callback=add)
    new.add_argument('source')
    new.add_argument('destination')
    new.add_argument('-k', '--keep', default=False, action='store_true')

    new = subparsers.add_parser('fetch')
    new.set_defaults(callback=fetch)
    new.add_argument('paths', nargs='+')

    new = subparsers.add_parser('pull')
    new.set_defaults(callback=pull)
    new.add_argument('source')
    new.add_argument('destination')
    new.add_argument('--mode', choices=list(PULL_MODES), help='how to pull the files from the hash.')

    new = subparsers.add_parser('gather')
    new.set_defaults(callback=gather)
    new.add_argument('source')
    new.add_argument('destination')

    new = subparsers.add_parser('update')
    new.set_defaults(callback=update)
    new.add_argument('source')
    new.add_argument('destination')
    new.add_argument('-k', '--keep', default=False, action='store_true')
    new.add_argument('--overwrite', default=False, action='store_true')

    new = subparsers.add_parser('blame')
    new.set_defaults(callback=blame)
    new.add_argument('path')
    new.add_argument('relative')

    add_storage_functions(subparsers.add_parser('storage'))

    args = vars(parser.parse_args())
    if 'callback' not in args:
        parser.print_help()
    else:
        callback = args.pop('callback')
        callback(**args)


def add_storage_functions(parser: ArgumentParser):
    subparsers = parser.add_subparsers()
    new = subparsers.add_parser('init')
    new.set_defaults(callback=init_storage)
