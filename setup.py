#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name='pytest-docker-db',
    version='0.1.1a2',
    author='Kyle Prestel',
    author_email='kprestel@gmail.com',
    maintainer='Kyle Prestel',
    maintainer_email='kprestel@gmail.com',
    license='MIT',
    url='https://github.com/kprestel/pytest-docker-db',
    description='A plugin to use docker databases for pytests',
    keywords='pytest docker database py.test postgres mysql',
    long_description=read('README.rst'),
    install_requires=['pytest>=3.1.1', 'docker>=3.1.0'],
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        'pytest11': [
            'docker-db = pytest_docker_db.plugin',
        ],
    },
)
