from pathlib import Path
from typing import Union, Tuple

from yaml import safe_load


class Include:
    # TODO: not safe
    key: str

    def __init__(self, value):
        self.value = value

    def read(self, parent: Union[Path, None]) -> Tuple[Union[Path, None], dict]:
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

    def __init__(self, value):
        super().__init__(Path(value).expanduser())

    def read(self, parent: Union[Path, None]) -> Tuple[Union[Path, None], dict]:
        path = self.value
        if not path.is_absolute():
            if parent is None:
                raise ValueError(
                    f"Can't read a config {path}: the path is relative and the parent "
                    f"doesn't have a well-defined disk location."
                )

            path = parent.parent / path

        with open(path, 'r') as file:
            return path, safe_load(file)
