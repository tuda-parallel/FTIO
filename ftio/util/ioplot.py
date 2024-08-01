import sys
from ftio.plot.plot_core import PlotCore


def main(args=sys.argv):
    plotter = PlotCore(args)
    plotter.plot_io()

if __name__ == "__main__":
    main(sys.argv)