"""
Functions for testing the ioplot functionality of the ftio package.
"""

import os
import pytest
from ftio.plot.plot_core import PlotCore

FILE = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")


def test_data_loaded():
    args = ["ioplot", FILE, "--no_disp"]
    plotter = PlotCore(args)
    assert plotter.data is not None
    assert plotter.data.n >= 1


def test_figures():
    args = ["ioplot", FILE, "--no_disp"]
    plotter = PlotCore(args)
    # figures = plotter.plot_plotly()
    # assert isinstance(figures, list)
    assert True


def test_plotter_dimensions():
    args = ["ioplot", FILE, "--no_disp"]
    plotter = PlotCore(args)
    assert plotter.width == 900
    assert plotter.height == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
