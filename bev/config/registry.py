import importlib
from typing import Optional, Type


_REGISTRY = {}


class RegistryError(Exception):
    pass


def register(name, cls: Optional[Type] = None):
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

    if '.' in name:
        raise ValueError('Names with dots are reserved for references to modules')
    if cls is None:
        return decorator
    return decorator(cls)


def find(name: str, kind: Type):
    if '.' in name:
        module, name = name.rsplit('.', 1)
        module = importlib.import_module(module)
        value = getattr(module, name)
        assert issubclass(value, kind), value
        return value

    if kind not in _REGISTRY:
        raise RegistryError(f'{kind} not found')
    local = _REGISTRY[kind]
    if name not in local:
        raise RegistryError(f'Invalid key "{name}" for "{kind.__name__}"')

    return local[name]


def add_type(kind):
    _REGISTRY[kind] = {}
    return kind
