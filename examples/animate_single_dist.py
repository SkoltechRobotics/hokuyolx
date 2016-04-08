'''Animates distances using single measurment mode'''
from hokuyolx import HokuyoLX
import matplotlib.pyplot as plt

DMAX = 10000

def update(laser, plot, text):
    timestamp, scan = laser.get_filtered_dist(dmax=DMAX)
    plot.set_data(*scan.T)
    text.set_text('t: %d' % timestamp)
    plt.draw()
    plt.pause(0.001)

def run():
    plt.ion()
    laser = HokuyoLX()
    ax = plt.subplot(111, projection='polar')
    plot = ax.plot([], [], '.')[0]
    text = plt.text(0, 1, '', transform=ax.transAxes)
    ax.set_rmax(DMAX)
    ax.grid(True)
    plt.show()
    while plt.get_fignums():
        update(laser, plot, text)
    laser.close()

if __name__ == '__main__':
    run()