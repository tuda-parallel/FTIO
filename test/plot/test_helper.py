import pytest
import plotly.graph_objects as go
from ftio.plot.helper import format_plot, format_plot_and_ticks, add_fig_row, add_fig_col

"""
Tests for class ftio/plot/helper.py
"""

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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])