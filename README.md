Flexible version control for files and folders.

# Install

The simplest way is to get it from PyPi:

```shell
pip install bev
```

Or if you want to try the latest version from GitHub:

```shell
git clone https://github.com/neuro-ml/bev.git
cd bev
pip install -e .

# or let pip handle the cloning:
pip install git+https://github.com/neuro-ml/bev.git
```

# Why not DVC?

[DVC](https://github.com/iterative/dvc) is a great project, and we took inspiration from it while designing `bev`.
However, out lab has several requirements that `DVC` doesn't meet:

1. Our data caches are spread across multiple HDDs - we need support for multiple cache locations
2. We have multiple machines, and each of them has a different storage configuration: locations, number of HDDs, their
   volumes - we need a flexible way of choosing the right config depending on the machine
3. Often we simultaneously conduct experiments on different versions of the same data - we need easy access to multiple
   version of the same data
4. The need for `dvc checkout` after `git checkout` is error-prone, because it can lead to situations when the data is
   not consistent with the current commit - we need a more constrained relation between data and `git`

`bev` supports all four out of the box!

However, if these requirements are not essential to your project, you may want to stick with `DVC` - its community and
tests coverage is much larger.

# Getting started

1. Create a config file named `.bev.yaml`:

```yaml
lv-426:
  storage:
    - root: /mount/hdd1/storage
    - root: /mount/hdd2/storage

fury-161:
  storage:
    - root: /nfs/vol1/data
    - root: /nfs/vol2/data
    - root: /nfs/vol8/data
```

Here `lv-426` and `fury-161` are two separate storage configurations. By default `bev` selects the appropriate
configuration based on the current hostname. So on a machine named `lv-426` the first config will be selected.

2. Add files to storage:

```shell
# folders
bev add path/to/some/folder .
# or separate files
bev add path/to/some/file.png .
```

check the repo:

```shell
ls
# folder.hash
# file.png.hash
```

3. Add the hashes to git and commit:

```shell
git add folder.hash file.png.hash
git commit -m "added essential files"
```

4. Access the files from Python:

```python
from bev import Repository

# initialize the repo
repo = Repository.from_root('path/to/repo')
# get the real path of `file.png`
image_path = repo.resolve('file.png', version='749335a')
# get the real path of `annotation/points.json` located inside of `folder`
points_path = repo.resolve('folder/annotation/points.json', version='749335a')
```
