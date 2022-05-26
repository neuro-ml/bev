import re


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
        assert len(v) == 1
        (k, v), = v.items()
        for kls in HostName.__subclasses__():
            if kls.key == k:
                return kls(v)

        raise ValueError(f'Invalid key "{k}" for hostname')


class StrHostName(HostName):
    key = 'str'

    def match(self, name) -> bool:
        return name == self.value


class RegexHostName(HostName):
    key = 'regex'

    def __init__(self, value):
        super().__init__(re.compile(value))

    def match(self, name) -> bool:
        return self.value.match(name) is not None
