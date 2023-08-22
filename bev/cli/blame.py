from datetime import datetime
from pathlib import Path

import typer
from tqdm.auto import tqdm
from typing_extensions import Annotated

from ..hash import from_hash, is_hash
from ..shortcuts import get_current_repo
from ..utils import call_git
from .app import app_command


@app_command
def blame(
        path: Annotated[Path, typer.Argument(help='Path to the hash')],
        relative: Annotated[str, typer.Argument(help='The relative path inside the hashed folder')]
):
    """Find the closest version which introduced a change to a value RELATIVE to the PATH"""

    repo = get_current_repo()
    path = Path(path).resolve().relative_to(repo.root)
    relative = str(relative)

    folder = path
    if is_hash(folder):
        folder = from_hash(folder)
    base = repo.get_key(folder, relative, version=repo.latest_version())

    idx = 0
    bar = tqdm()
    while True:
        idx += 1
        output = call_git(f'git log -n 1 --skip {idx} --pretty=format:%H,%ct -- {path}', repo.root, True)
        if not output:
            break

        commit, time = output.split(',', 1)
        bar.update()
        bar.set_description_str(str(datetime.fromtimestamp(int(time))))

        current = repo.load_tree(path, commit)
        if relative not in current or current[relative] != base:
            bar.close()
            print(call_git(f"git log --format='%an <%ae> at %aD' {commit}^!", repo.root, True))
            return

    bar.close()
    print(call_git(f"git log -n 1 --format='%an <%ae> at %aD' -- {path}", repo.root, True))
