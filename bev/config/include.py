from pathlib import Path

from yaml import safe_load


class Include:
    # TODO: not safe
    key: str

    def __init__(self, value):
        self.value = value

    def read(self) -> dict:
        raise NotImplementedError

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, Include):
            return v

        assert isinstance(v, dict), f'Not a dict: {v}'
        assert len(v) == 1
        (k, v), = v.items()
        # TODO: not safe
        for kls in Include.__subclasses__():
            if kls.key == k:
                return kls(v)

        raise ValueError(f'Invalid key "{k}" for hostname')


class FileInclude(Include):
    key = 'file'

    def read(self) -> dict:
        with open(Path(self.value).expanduser(), 'r') as file:
            return safe_load(file)
