#!/usr/bin/env python3

from setuptools import find_packages, setup

setup(
    name='ytplay',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ytplay = ytplay:main',
        ],
    },

    author='Allen Li',
    author_email='darkfeline@felesatra.moe',
    description='',
    license='',
    url='',
)
