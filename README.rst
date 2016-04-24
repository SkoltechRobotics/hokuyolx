*********
Hokuyo LX
*********

A Python module for working with Hokuyo LX laser scanners.

.. image:: https://readthedocs.org/projects/hokuyolx/badge/?version=latest
    :target: http://hokuyolx.readthedocs.org/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/pypi/v/hokuyolx.svg
    :target: https://pypi.python.org/pypi/hokuyolx
    :alt: PyPI version

.. image:: https://img.shields.io/github/license/mashape/apistatus.svg
    :target: https://github.com/SkRobo/hokuyolx/blob/master/LICENSE
    :alt: MIT License

============
Introduction
============

This module aims to implement communication protocol with Hokuyo
laser rangefinder scaners, specifically with the following models:
UST-10LX, UST-20LX, UST-30LX.
It was tested only with UST-10LX but should work with others as well.
It's Python 2 and 3 compatible but was mainly tested using Python 3.

For protocol specifications please refer to the following documents:

- http://www.hokuyo-aut.jp/02sensor/07scanner/download/pdf/UTM-30LX-EW_protocol_en.pdf

- https://www.hokuyo-aut.jp/02sensor/07scanner/download/pdf/UST_protocol_en.pdf

==========
Installing
==========

You can install hokuyolx using ``pip``::

    $ sudo pip install hokuyolx

Or for Python 3::

    $ sudo pip3 install hokuyolx

=============
Documentation
=============

View the latest hokuyolx documentation at http://hokuyolx.rtfd.org/.

=============
Usage example
=============

Simple example::

    >>> from hokuyolx import HokuyoLX
    >>> laser = HokuyoLX()
    >>> timestamp, scan = laser.get_dist() # Single measurment mode
    >>> # Continous measurment mode
    >>> for timestamp, scan in laser.iter_dist(10):
    ...     print(timestamp)

In addition to it you can view example applications inside
`examples <https://github.com/SkRobo/hokuyolx/tree/master/examples>`_ directory.
