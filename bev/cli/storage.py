import ast
import hashlib
import inspect
from pathlib import Path

from connectome.storage.config import init_storage as _init_storage


def init_storage():
    path = Path()
    if list(path.iterdir()):
        print('The folder is not empty')
        exit(1)

    algos = hashlib.algorithms_guaranteed
    default_algo = 'sha256'

    print(f'Hash algorithm (Press Enter for {default_algo}, ? for options): ', end='')
    option = input().strip() or default_algo
    while option not in algos:
        if option != '?':
            print(f'Unknown algorithm "{option}"')
        print('Available algorithms:', ', '.join(algos))
        print('Hash algorithm (Press Enter for sha256, ? for options): ', end='')
        option = input().strip() or default_algo

    algo = getattr(hashlib, option)
    try:
        params = {x.name: x.default for x in list(inspect.signature(algo).parameters.values())[1:]}
    except ValueError:
        params = {}

    kwargs = {}
    if params:
        all_params = '\n'.join(f'{k}: {v}' for k, v in kwargs.items())
        print(f'Default hash parameters:\n{all_params}\nModify hash parameters? (y/N): ', end='')
        if parse_yes():
            for param, default in params.items():
                print(f'Algorithm parameter "{param}" (Press Enter for {default}): ', end='')
                value = input().strip()
                if value:
                    value = ast.literal_eval(value)
                    if value != default:
                        kwargs[param] = value

    digest_size = algo(**kwargs).digest_size
    half_digest = digest_size // 2
    default_levels = 1, half_digest - 1, half_digest
    print(f'Folder levels. Must sum to {digest_size} (Press Enter for {default_levels}): ', end='')
    levels = parse_levels(default_levels, digest_size)

    assert 'name' not in kwargs
    kwargs['name'] = option
    _init_storage(path, algorithm=kwargs, levels=levels, exist_ok=True)


def parse_yes():
    raw = input().strip()
    value = raw.lower()
    while True:
        if value in ['y', 'yes']:
            return True
        if value in ['n', 'no', '']:
            return False

        print('Unknown option:', raw, 'Try again: ', end='')
        raw = input().strip()
        value = raw.lower()


def parse_levels(default, size):
    levels = input().strip()
    while True:
        if not levels:
            return default

        levels = ast.literal_eval(levels)
        if sum(levels) == size:
            return levels

        print(f"The levels don't sum to {size}. Try again: ", end='')
        levels = input().strip()
