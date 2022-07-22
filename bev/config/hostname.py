import re

from .registry import register, find, add_type


@add_type
class HostName:
    key: str

    def __init__(self, value):
        self.value = value

    def match(self, name) -> bool:
        raise NotImplementedError

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, HostName):
            return v
        if isinstance(v, str):
            return StrHostName(v)

        assert isinstance(v, dict), f'Not a dict: {v}'
        assert len(v) == 1, v
        (k, v), = v.items()

        return find(HostName, k)(v)


@register('str')
class StrHostName(HostName):
    def match(self, name) -> bool:
        return name == self.value


@register('regex')
class RegexHostName(HostName):
    def match(self, name) -> bool:
        return re.match(self.value, name) is not None
