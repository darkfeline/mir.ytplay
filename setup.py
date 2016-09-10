#!/usr/bin/env python3

from setuptools import find_packages, setup

setup(
    name='mir.ytplay',
    version='0.1.0',
    description='Stream music from YouTube.',
    url='',
    author='Allen Li',
    author_email='darkfeline@felesatra.moe',
    license='',

    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ytplay = mir.ytplay:main',
        ],
    },

)
