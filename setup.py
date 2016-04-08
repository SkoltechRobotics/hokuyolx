#!/usr/bin/python3
from distutils.core import setup

setup(
    name = 'hokuyolx',
    packages = ['hokuyolx'],
    version = '0.8',
    description = 'Module for working with Hokuyo LX laser scanners.',
    author='Artyom Pavlov',
    author_email='newpavlov@gmail.com',
    url='https://github.com/SkRobo/hokuyolx',
    license='MIT',
    install_requires=[
        'numpy',
    ],
    zip_safe=True,
)
