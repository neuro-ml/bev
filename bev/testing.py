from pathlib import Path
from tempfile import TemporaryDirectory


def create_structure(root, entries):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)

    if isinstance(entries, dict):
        entries = entries.items()
    else:
        entries = [[x, None] for x in entries]

    for entry, content in entries:
        if entry.endswith('/'):
            if content is None:
                (root / entry).mkdir(parents=True)
                continue

        (root / entry).parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            content = ''

        with open(root / entry, 'w') as file:
            file.write(content)

    return root


class TempDir(TemporaryDirectory):
    def __enter__(self):
        return Path(super().__enter__())
