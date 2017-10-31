#!/usr/bin/env python
'''Python setup.py'''

import ast
import re
from setuptools import setup, find_packages

import multiplexer

DEPENDENCIES = [
    'boto3',
    'pyyaml',
    'PyGithub',
]

STYLE_REQUIRES = [
    'flake8>=2.5.4',
    'pylint>=1.5.5',
]

TESTS_REQUIRE = [
    'pytest',
    'moto',
    'nose',
]


setup(
    name='aws-cd-multiplex',
    description='Merge multiple repositories into single artifact for AWS CodeDeploy.',
    keywords='',
    version=multiplexer.__version__,
    tests_require=TESTS_REQUIRE + STYLE_REQUIRES,
    install_requires=DEPENDENCIES,
    packages=find_packages(exclude=['tests']),
    classifiers=[
        "Programming Language :: Python :: 3.5",
    ],
    license='Apache 2.0',
    author="Rackers",
    maintainer_email="fps@rackspace.com",
    entry_points={
        'console_scripts': [
            'multiplexer=multiplexer.shell:main'
        ]
    },
)
