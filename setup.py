#!/usr/bin/env python3

from setuptools import find_packages, setup

setup(
    name='mir.ytplay',
    version='0.1.1',
    description='Stream music from YouTube.',
    long_description='',
    keywords='',
    url='',
    author='Allen Li',
    author_email='darkfeline@felesatra.moe',
    license='',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet',
    ],

    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ytplay = mir.ytplay:main',
        ],
    },

)
