"""
Functions for testing the ioplot functionality of the ftio package.
"""

import os
import numpy as np
import pytest
import plotly.graph_objects as go

from ftio.plot.units import set_unit
from ftio.plot.plot_core import PlotCore
from ftio.plot.helper import format_plot, format_plot_and_ticks, add_fig_row, add_fig_col
from ftio.plot.spectrum import plot_spectrum, plot_both_spectrums, plot_one_spectrum
from ftio.plot.dash_files.constants import graph_mode, id, io_mode, legend_group

FILE = os.path.join(os.path.dirname(__file__), '../examples/tmio/JSONL/8.jsonl')


def test_data_loaded():
    args = ['ioplot', FILE, '--no_disp']
    plotter = PlotCore(args)
    assert plotter.data is not None
    assert plotter.data.n >= 1


def test_figures():
    args = ['ioplot', FILE, '--no_disp']
    plotter = PlotCore(args)
    figures = plotter.plot_plotly()
    assert isinstance(figures, list)


def test_plotter_dimensions():
    args = ['ioplot', FILE, '--no_disp']
    plotter = PlotCore(args)
    assert plotter.width == 900
    assert plotter.height == 400


def test_get_figure_time():
    args = ['ioplot', FILE, '--no_disp']
    plotter = PlotCore(args)
    plotter.plot_plotly()
    time_figures = plotter.get_figure('time.html')
    assert isinstance(time_figures, list)


# Unit tests

def test_units_empty():
    arr = np.array([])
    unit, order = set_unit(arr)
    assert unit == 'B/s'
    assert order == 1


def test_units_gigabyte():
    arr = np.array([10000000000.0, 20000000000.0])
    unit, order = set_unit(arr)
    assert unit == 'GB/s'
    assert order == 1e-09


def test_units_megabyte():
    arr = np.array([10000000.0, 20000000.0])
    unit, order = set_unit(arr)
    assert unit == 'MB/s'
    assert order == 1e-06


def test_units_kilobyte():
    arr = np.array([10000.0, 20000.0])
    unit, order = set_unit(arr)
    assert unit == 'KB/s'
    assert order == 0.001


def test_units_byte():
    arr = np.array([100, 200])
    unit, order = set_unit(arr)
    assert unit == 'B/s'
    assert order == 1


def test_units_suffix():
    arr = np.array([10000000000.0])
    unit, order = set_unit(arr, suffix='tuda')
    assert unit == 'Gtuda'


# Format plot tests

def test_format_plot_and_ticks_returnformat():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=(1, 2, 3), y=(4, 5, 6)))
    result = format_plot_and_ticks(fig)
    assert isinstance(result, go.Figure)


def test_format_plot_and_ticks_legend_false():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=(1, 2, 3), y=(4, 5, 6)))
    result = format_plot_and_ticks(fig, legend=False)
    assert isinstance(result, go.Figure)


def test_format_plot_returnformat():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=(1, 2, 3), y=(4, 5, 6)))
    result = format_plot(fig)
    assert isinstance(result, go.Figure)
    assert result.layout.plot_bgcolor == 'white'


def test_format_plot_font():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=(1, 2, 3), y=(4, 5, 6)))
    result = format_plot(fig, font_size=24)
    assert result.layout.font.size == 24


def test_add_fig_row():
    fig = add_fig_row(1, 10)
    assert isinstance(fig, go.Figure)


def test_add_fig_row_onefig():
    fig = add_fig_row(10, onefig=True)
    assert isinstance(fig, go.Figure)


def test_add_fig_col():
    fig = add_fig_col(1, 10)
    assert isinstance(fig, go.Figure)


# Spectrum tests

def test_plot_spectrum():
    amp = np.array((1.0, 2.0, 3.0, 2.0, 1.0))
    freq = np.array((0.0, 0.25, 0.5, 0.75, 1.0))
    fig, name = plot_spectrum(amp, freq, mode='Amplitude')
    assert isinstance(fig, go.Figure)
    assert 'Amplitude' in name


def test_plot_spectrum_power():
    amp = np.array((1.0, 2.0, 3.0, 2.0, 1.0))
    freq = np.array((0.0, 0.25, 0.5, 0.75, 1.0))
    fig, name = plot_spectrum(amp, freq, mode='Power')
    assert isinstance(fig, go.Figure)
    assert 'Power' in name


def test_plot_spectrum_percentnormal():
    amp = np.array((1.0, 2.0, 3.0, 2.0, 1.0))
    freq = np.array((0.0, 0.25, 0.5, 0.75, 1.0))
    fig, name = plot_spectrum(amp, freq, percent=True)
    assert isinstance(fig, go.Figure)
    assert '%' in name


def test_plot_both_spectrums():
    class Args:
        psd = False
    args = Args()
    amp = np.array((1.0, 2.0, 3.0, 2.0, 1.0, 0.5))
    freq = np.array((0.0, 0.2, 0.4, 0.6, 0.8, 1.0))
    fig, names = plot_both_spectrums(args, amp, freq)
    assert isinstance(fig, go.Figure)
    assert isinstance(names, list)
    assert len(names) == 2


def test_plot_one_spectrum():
    amp = np.array((1.0, 2.0, 3.0, 2.0, 1.0, 0.5))
    freq = np.array((0.0, 0.2, 0.4, 0.6, 0.8, 1.0))
    fig = plot_one_spectrum(psd_flag=False, freq=freq, amp=amp, full=True)
    assert isinstance(fig, go.Figure)


def test_plot_one_spectrum_full_false():
    amp = np.array((1.0, 2.0, 3.0, 2.0, 1.0, 0.5))
    freq = np.array((0.0, 0.2, 0.4, 0.6, 0.8, 1.0))
    fig = plot_one_spectrum(psd_flag=False, freq=freq, amp=amp, full=False)
    assert isinstance(fig, go.Figure)


def test_plot_one_spectrum_psd():
    amp = np.array((1.0, 2.0, 3.0, 2.0, 1.0, 0.5))
    freq = np.array((0.0, 0.2, 0.4, 0.6, 0.8, 1.0))
    fig = plot_one_spectrum(psd_flag=True, freq=freq, amp=amp)
    assert isinstance(fig, go.Figure)


# Constants tests

def test_graph_mode_constants():
    assert graph_mode.SUM == 'sum'
    assert graph_mode.AVERAGE == 'average'
    assert graph_mode.INDIVIDUAL == 'individual'
    assert len(graph_mode.ALL_MODES) == 3
    assert graph_mode.SUM in graph_mode.ALL_MODES
    assert graph_mode.AVERAGE in graph_mode.ALL_MODES
    assert graph_mode.INDIVIDUAL in graph_mode.ALL_MODES


def test_id_constants():
    assert id.BUTTON_SHOW == 'button-show'
    assert id.CHECKLIST_IO_MODE == 'checklist-io-mode'
    assert id.DIV_SYNC_READ == 'div-sync-read'
    assert id.DIV_SYNC_WRITE == 'div-sync-write'
    assert id.DIV_ASNYC_READ == 'div-async-read'
    assert id.DIV_ASYNC_WRITE == 'div-async-write'
    assert id.DIV_IO_TIME == 'div-io-time'
    assert len(id.DIV_IO_BY_IO_MODE) == 5
    assert id.DROPDOWN_FILE == 'dropdown-file'
    assert id.STORE_FIGURES_ASYNC_READ == 'store-figures-' + io_mode.ASYNC_READ
    assert id.STORE_FIGURES_ASYNC_WRITE == 'store-figures-' + io_mode.ASYNC_WRITE
    assert id.STORE_FIGURES_SYNC_READ == 'store-figures-' + io_mode.SYNC_READ
    assert id.STORE_FIGURES_SYNC_WRITE == 'store-figures-' + io_mode.SYNC_WRITE
    assert id.STORE_FIGURES_TIME == 'store-figures-' + io_mode.TIME
    assert len(id.STORE_FIGURES_BY_IO_MODE) == 5
    assert id.TYPE_DYNAMIC_GRAPH == 'dynamic-graph'
    assert id.TYPE_DYNAMIC_UPDATER_ASYNC_READ == 'dynamic-updater-' + io_mode.ASYNC_READ
    assert id.TYPE_DYNAMIC_UPDATER_ASYNC_WRITE == 'dynamic-updater-' + io_mode.ASYNC_WRITE
    assert id.TYPE_DYNAMIC_UPDATER_SYNC_READ == 'dynamic-updater-' + io_mode.SYNC_READ
    assert id.TYPE_DYNAMIC_UPDATER_SYNC_WRITE == 'dynamic-updater-' + io_mode.SYNC_WRITE
    assert id.TYPE_DYNAMIC_UPDATER_TIME == 'dynamic-updater-' + io_mode.TIME
    assert len(id.TYPE_DYNAMIC_UPDATER_BY_IO_MODE) == 5


def test_io_mode_constants():
    assert io_mode.ASYNC_READ == 'read_async'
    assert io_mode.ASYNC_WRITE == 'write_async'
    assert io_mode.SYNC_READ == 'read_sync'
    assert io_mode.SYNC_WRITE == 'write_sync'
    assert io_mode.TIME == 'time'
    assert len(io_mode.ALL_MODES) == 5
    assert io_mode.ASYNC_WRITE in io_mode.ALL_MODES
    assert io_mode.ASYNC_READ in io_mode.ALL_MODES
    assert io_mode.SYNC_WRITE in io_mode.ALL_MODES
    assert io_mode.SYNC_READ in io_mode.ALL_MODES
    assert io_mode.TIME in io_mode.ALL_MODES
    assert len(io_mode.MODE_STRING_BY_MODE) == 5


def test_legend_group_constants():
    assert legend_group.ACTUAL_AVERAGE == 'actual_average'
    assert legend_group.ACTUAL_SUM == 'actual_sum'
    assert legend_group.ACTUAL_INDIVIDUAL == 'actual_individual'
    assert legend_group.REQUIRED_AVERAGE == 'required_average'
    assert legend_group.REQUIRED_SUM == 'required_sum'
    assert legend_group.REQUIRED_INDIVIDUAL == 'required_individual'
    assert legend_group.ACTUAL_AVERAGE_TITLE == 'Actual average'
    assert legend_group.ACTUAL_SUM_TITLE == 'Actual sum'
    assert legend_group.ACTUAL_INDIVIDUAL_TITLE == 'Actual individual'
    assert legend_group.REQUIRED_AVERAGE_TITLE == 'Required average'
    assert legend_group.REQUIRED_SUM_TITLE == 'Required sum'
    assert legend_group.REQUIRED_INDIVIDUAL_TITLE == 'Required individual'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
