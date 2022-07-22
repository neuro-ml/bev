from typing import Type

_REGISTRY = {}


def register(name, cls: Type = None):
    def decorator(kls: Type):
        if not isinstance(kls, type):
            raise TypeError(f'{kls} is not a type')

        match = {kind for kind in _REGISTRY if issubclass(kls, kind)}
        if len(match) != 1:
            raise TypeError(f"Couldn't match the type {kls}")
        kind, = match

        local = _REGISTRY[kind]
        if name in local:
            raise ValueError(f'The key "{name}" if already reserved by {local[name]}')
        local[name] = kls

        return kls

    if cls is None:
        return decorator
    return decorator(cls)


def find(kind: Type, name: str):
    if kind not in _REGISTRY:
        raise ValueError(f'{kind} not found')
    local = _REGISTRY[kind]
    if name not in local:
        raise ValueError(f'Invalid key "{name}" for "{kind.__name__}"')

    return local[name]


def add_type(kind):
    _REGISTRY[kind] = {}
    return kind
