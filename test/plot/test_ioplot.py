"""
Functions for testing the ioplot functionality of the ftio package.

Author: lucasch03
Copyright (c) 2024-2026 TU Darmstadt, Germany
Version: 0.0.8
Date: Jan 2026

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import os

import pytest

from ftio.plot.plot_core import PlotCore

FILE = os.path.join(os.path.dirname(__file__), "../../examples/tmio/JSONL/8.jsonl")


def test_data_loaded():
    args = ["ioplot", FILE, "--no_disp"]
    plotter = PlotCore(args)
    assert plotter.data is not None
    assert plotter.data.n >= 1


def test_figures():
    args = ["ioplot", FILE, "--no_disp"]
    plotter = PlotCore(args)
    figures = plotter.plot_plotly()
    assert isinstance(figures, list)


def test_plotter_dimensions():
    args = ["ioplot", FILE, "--no_disp"]
    plotter = PlotCore(args)
    assert plotter.width == 900
    assert plotter.height == 400


def test_get_figure_time():
    args = ["ioplot", FILE, "--no_disp"]
    plotter = PlotCore(args)
    plotter.plot_plotly()
    time_figures = plotter.get_figure("time.html")
    assert isinstance(time_figures, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
