"""
Author: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Version: 0.0.8
Date: Feb 2024

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import sys

from ftio.plot.plot_core import PlotCore


def main(args=sys.argv):
    plotter = PlotCore(args)
    plotter.plot_io()


if __name__ == "__main__":
    main(sys.argv)
