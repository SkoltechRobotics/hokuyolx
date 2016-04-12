'''This module aims to implement communication protocol with Hokuyo
laser rangefinder scaners, specifically with the following models:
UST-10LX, UST-20LX, UST-30LX. It was tested only with UST-10LX but should work
with others as well. For protocol specifications please refer to the following
documents:

- http://www.hokuyo-aut.jp/02sensor/07scanner/download/pdf/UTM-30LX-EW_protocol_en.pdf

- https://www.hokuyo-aut.jp/02sensor/07scanner/download/pdf/UST_protocol_en.pdf

Usage example:

>>> from hokuyolx import HokuyoLX
>>> laser = HokuyoLX()
>>> timestamp, scan = laser.get_dist() # Single measurment mode
>>> # Continous measurment mode
>>> for timestamp, scan in laser.iter_dist(10):
...     print(timestamp)

For further information please refer to HokuyoLX class documentation
'''
from .hokuyo import HokuyoLX
