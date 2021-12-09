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

# Getting started

1. Choose a folder for your repository and create a basic config (`.bev.yml`):

```yaml
main:
  storage: /path/to/storage/folder

meta:
  hash: sha256
```

2. Run `init`

```shell
bev init
```

3. Add files to bev

```shell
bev add /path/to/some/file.json .
bev add /path/to/some/folder/ .
bev add /path/to/some/image.png .
```

4. ... and to git

```shell
git add file.json.hash folder.hash image.png.hash
git commit -m "added files"
```

5. Access the files from python

```python
import imageio
from bev import Repository

# `version` can be a commit hash or a git tag 
repo = Repository('/path/to/repo', version='8a7fe6')
image = imageio.imread(repo.resolve('image.png'))
```

### Advanced usage

Here are some tutorials that cover more advanced configuration, including multiple storage locations and machines:

1. [Create a repository](https://github.com/neuro-ml/bev/wiki/Creating-a-repository) - needed only at first time setup
2. [Adding files](https://github.com/neuro-ml/bev/wiki/Adding-files)
3. [Accessing files](https://github.com/neuro-ml/bev/wiki/Accessing-the-stored-files)

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
