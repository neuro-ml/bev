import re

from .compat import core_schema
from .registry import RegistryError, add_type, find, register


@add_type
class HostName:
    def __init__(self, value):
        self.value = value

    def match(self, name) -> bool:
        raise NotImplementedError

    @classmethod
    def __get_validators__(cls):
        yield cls._validate

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return core_schema.no_info_plain_validator_function(cls._validate)

    @classmethod
    def _validate(cls, v):
        if isinstance(v, HostName):
            return v
        if isinstance(v, str):
            return StrHostName(v)

        assert isinstance(v, dict), f'Not a dict: {v}'
        assert len(v) == 1, v
        (k, v), = v.items()

        try:
            return find(k, HostName)(v)
        except RegistryError as e:
            raise ValueError(str(e)) from e


@register('str')
class StrHostName(HostName):
    def match(self, name) -> bool:
        return name == self.value


@register('regex')
class RegexHostName(HostName):
    def match(self, name) -> bool:
        return re.match(self.value, name) is not None
