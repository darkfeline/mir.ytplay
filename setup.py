#!/usr/bin/env python3

from setuptools import setup

setup(
    name='mir.ytplay',
    version='0.1.2',
    description='Stream music from YouTube.',
    long_description='',
    keywords='',
    url='https://github.com/darkfeline/mir.ytplay',
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

    py_modules=['mir.ytplay'],
    entry_points={
        'console_scripts': [
            'ytplay = mir.ytplay:main',
        ],
    },

)
