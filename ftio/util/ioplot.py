import sys
from ftio.plot.plot_core import plot_core


def main(args=sys.argv):
    plotter = plot_core(args)
    plotter.plot_io()

if __name__ == "__main__":
    main(sys.argv)