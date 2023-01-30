from pathlib import Path

from setuptools import setup, find_packages

classifiers = [
    'Development Status :: 5 - Production/Stable',
    'License :: OSI Approved :: Apache Software License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3 :: Only',
]

root = Path(__file__).resolve().parent
with open(root / 'README.md', encoding='utf-8') as file:
    long_description = file.read()
with open(root / 'requirements.txt', encoding='utf-8') as file:
    requirements = file.read().splitlines()
# get the current version
with open(root / 'bev/__version__.py', encoding='utf-8') as file:
    scope = {}
    exec(file.read(), scope)
    __version__ = scope['__version__']

setup(
    name='bev',
    packages=find_packages(include=('bev',)),
    include_package_data=True,
    version=__version__,
    description='A small manager for versioned data',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    url='https://github.com/neuro-ml/bev',
    download_url='https://github.com/neuro-ml/bev/archive/v%s.tar.gz' % __version__,
    keywords=['data', 'version control'],
    classifiers=classifiers,
    install_requires=requirements,
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'bev = bev.cli.entrypoint:entrypoint',
        ],
    },
)
