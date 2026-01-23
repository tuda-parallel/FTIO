import numpy as np
import pytest
import plotly.graph_objects as go
from ftio.plot.spectrum import plot_spectrum, plot_both_spectrums, plot_one_spectrum

"""
Tests for class ftio/plot/spectrum.py
"""

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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])