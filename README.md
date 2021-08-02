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

Here are some tutorials to quickly get you started:

1. [Create a repository](https://github.com/neuro-ml/bev/wiki/Creating-a-repository) - needed only at first time setup
2. [Adding files](https://github.com/neuro-ml/bev/wiki/Adding-files)
3. [Accessing files](https://github.com/neuro-ml/bev/wiki/Accessing-the-stored-files)
