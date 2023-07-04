import importlib
from pathlib import Path
from typing import Tuple, Union

from yaml import safe_load

from .compat import core_schema
from .registry import RegistryError, add_type, find, register


@add_type
class Include:
    def __init__(self, value, optional: bool):
        self.value = value
        self.optional = optional

    def read(self, parent: Union[Path, None]) -> Tuple[Union[Path, None], Union[dict, None]]:
        raise NotImplementedError

    @classmethod
    def __get_validators__(cls):
        yield cls._validate

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return core_schema.no_info_plain_validator_function(cls._validate)

    @classmethod
    def _validate(cls, v):
        if isinstance(v, Include):
            return v

        assert isinstance(v, dict), f'Not a dict: {v}'
        optional = v.pop('optional', False)
        assert len(v) == 1, v
        (k, v), = v.items()

        try:
            return find(k, Include)(v, optional)
        except RegistryError as e:
            raise ValueError(str(e)) from e


@register('file')
class FileInclude(Include):
    def __init__(self, value, optional):
        super().__init__(Path(value).expanduser(), optional)

    def read(self, parent: Union[Path, None]) -> Tuple[Union[Path, None], Union[dict, None]]:
        path = self.value
        if not path.is_absolute():
            if parent is None:
                raise ValueError(
                    f"Can't read a config {path}: the path is relative and the parent "
                    f"doesn't have a well-defined disk location."
                )

            path = parent.parent / path

        if path.exists():
            with open(path, 'r') as file:
                return path, safe_load(file)

        return None, None


@register('module')
class ModuleInclude(Include):
    def read(self, parent: Union[Path, None]) -> Tuple[Union[Path, None], Union[dict, None]]:
        path = self._find(self.value)
        if path is None:
            return None, None

        with open(path, 'r') as file:
            return path, safe_load(file)

    @staticmethod
    def _find(value):
        # TODO: default file name
        value, file = value.split(':')
        parts = value.split('.')
        name = ''
        while parts:
            if name:
                name += '.'
            name += parts.pop(0)
            try:
                module = importlib.import_module(name)
            except ImportError:
                continue

            path = Path(module.__path__[0], *parts, file)
            if path.exists():
                return path
