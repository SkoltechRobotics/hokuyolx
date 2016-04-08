'''Animates distances using single measurment mode'''
from hokuyolx import HokuyoLX
import matplotlib.pyplot as plt

DMAX = 10000
IMIN = 300.
IMAX = 2000.

def get_colors(intens):
    max_val = intens.max()
    return np.repeat(intens, 3).reshape((4,3))/max_val 

def update(laser, plot, text):
    timestamp, scan = laser.get_filtered_intens(dmax=DMAX)
    plot.set_offsets(scan[:, :2])
    plot.set_array(scan[:, 2])
    text.set_text('t: %d' % timestamp)
    plt.show()
    plt.pause(0.001)

def run():
    plt.ion()
    laser = HokuyoLX()
    ax = plt.subplot(111, projection='polar')
    plot = ax.scatter([0, 1], [0, 1], s=5, c=[IMIN, IMAX], cmap=plt.cm.Greys_r, lw=0)
    text = plt.text(0, 1, '', transform=ax.transAxes)
    ax.set_rmax(DMAX)
    ax.grid(True)
    plt.show()
    while plt.get_fignums():
        update(laser, plot, text)
    laser.close()

if __name__ == '__main__':
    run()