try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name = 'hokuyolx',
    packages = ['hokuyolx'],
    version = '0.8.3',
    description = 'Module for working with Hokuyo LX laser scanners.',
    author='Artyom Pavlov',
    author_email='newpavlov@gmail.com',
    url='https://github.com/SkRobo/hokuyolx',
    license='MIT',
    install_requires=['numpy'],
    zip_safe=True,
    long_description='This module aims to implement communication protocol '
        'with Hokuyo laser rangefinder scaners, specifically with the'
        'following models: UST-10LX, UST-20LX, UST-30LX. It was tested only '
        'with UST-10LX but should work with others as well. It\'s '
        'Python 2 and 3 compatible but was mainly tested using Python 3.',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: System :: Hardware',
    ],
)
