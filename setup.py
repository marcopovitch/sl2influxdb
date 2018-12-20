#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='sl2influxdb',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'seedlink2influxdb = sl2influxdb.seedlink2influxdb:main',
        ],
    },
)
