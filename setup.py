from setuptools import setup, find_packages

from bev.__version__ import __version__

classifiers = '''Programming Language :: Python :: 3.6
Programming Language :: Python :: 3.7
Programming Language :: Python :: 3.8
Programming Language :: Python :: 3.9'''

with open('README.md', encoding='utf-8') as file:
    long_description = file.read()

with open('requirements.txt', encoding='utf-8') as file:
    requirements = file.read().splitlines()

setup(
    name='bev',
    packages=find_packages(include=('bev*',)),
    include_package_data=True,
    version=__version__,
    description='A small manager for versioned data',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    url='https://github.com/neuro-ml/bev',
    download_url='https://github.com/neuro-ml/bev/archive/v%s.tar.gz' % __version__,
    keywords=['data', 'version control'],
    classifiers=classifiers.splitlines(),
    install_requires=requirements,
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'bev = bev.cli.entrypoint:entrypoint',
        ],
    },
)
