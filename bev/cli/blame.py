from pathlib import Path
from datetime import datetime

from tqdm import tqdm

from ..hash import from_hash, is_hash
from ..shortcuts import get_current_repo
from ..utils import call


def blame(path: Path, relative: str):
    repo = get_current_repo()
    path = Path(path).resolve().relative_to(repo.root)
    relative = str(relative)

    folder = path
    if is_hash(folder):
        folder = from_hash(folder)
    base = repo.get_key(folder, relative, version=repo.current_version)

    idx = 0
    bar = tqdm()
    while True:
        idx += 1
        output = call(f'git log -n 1 --skip {idx} --pretty=format:%H,%ct -- {path}', repo.root)
        if not output:
            break

        commit, time = output.split(',', 1)
        bar.update()
        bar.set_description_str(str(datetime.fromtimestamp(int(time))))

        current = repo.load_tree(path, commit)
        if relative not in current or current[relative] != base:
            bar.close()
            print(call(f"git log --format='%an <%ae> at %aD' {commit}^!", repo.root))
            return

    bar.close()
    print(call(f"git log -n 1 --format='%an <%ae> at %aD' -- {path}", repo.root))
