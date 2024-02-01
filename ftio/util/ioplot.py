import sys
from ftio.plot_io.plot_core import plot_core


def main(args=sys.argv):
    plotter = plot_core(args)
    plotter.plot()

if __name__ == "__main__":
    main(sys.argv)