"""
STFT Plotting functions for FTIO.

Author: Ahmad Tarraf
Copyright (c) 2026 TU Darmstadt, Germany
Version: v0.0.8
Date: Feb 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go

from ftio.freq._stft import compute_stft
from ftio.plot.helper import format_plot
from ftio.plot.units import set_unit


def plot_stft(args, prediction, b_sampled, fs, stft_data=None):
    """
    Plots the STFT of the signal, its reconstruction, and the dominant frequency tracking
    using the specified engine (Plotly or Matplotlib).

    Args:
        args (Namespace): Parsed arguments.
        prediction (Prediction): Prediction object containing detected frequencies.
        b_sampled (np.ndarray): Uniformly sampled bandwidth data.
        fs (float): Sampling frequency in Hz.
        stft_data (tuple, optional): Precomputed (f, t, Zxx) from STFT. Defaults to None.

    Returns:
        list: A list of figure objects (Plotly or Matplotlib).
    """
    if stft_data is not None:
        f, t_stft, Zxx = stft_data
    else:
        f, t_stft, Zxx = compute_stft(b_sampled, fs)

    Zxx_mag = np.abs(Zxx)

    if "mat" in args.engine:
        return [
            plot_stft_matplotlib_spectrogram(f, t_stft, Zxx_mag),
            plot_stft_matplotlib_reconstruction(args, prediction, b_sampled, fs, t_stft),
            plot_stft_matplotlib_dominant_freq(args, prediction, b_sampled, fs, t_stft),
        ]
    elif "plotly" in args.engine:
        return [
            plot_stft_plotly_spectrogram(f, t_stft, Zxx_mag),
            plot_stft_plotly_reconstruction(args, prediction, b_sampled, fs, t_stft),
            plot_stft_plotly_dominant_freq(args, prediction, b_sampled, fs, t_stft),
        ]


def plot_stft_matplotlib_spectrogram(f, t, Zxx_mag):
    """Generates an STFT magnitude spectrogram using Matplotlib."""
    fig = plt.figure(figsize=(10, 6))
    plt.pcolormesh(t, f, Zxx_mag, shading="gouraud")
    plt.title("STFT Magnitude")
    plt.ylabel("Frequency (Hz)")
    plt.xlabel("Time (s)")
    plt.colorbar(label="Magnitude")
    return fig


def plot_stft_plotly_spectrogram(f, t, Zxx_mag):
    """Generates an STFT magnitude spectrogram using Plotly."""
    fig = go.Figure(data=go.Heatmap(x=t, y=f, z=Zxx_mag, colorscale="Viridis"))

    fig.update_layout(
        title="STFT Magnitude",
        xaxis_title="Time (s)",
        yaxis_title="Frequency (Hz)",
    )
    return fig


def reconstruct_stft_signal(prediction, fs, n_samples, t_stft):
    """
    Reconstructs the time-domain signal by stitching together the dominant
    sinusoids identified in each STFT window.

    Args:
        prediction (Prediction): Object containing 'dominant_freq', 'amp', and 'phi' arrays.
        fs (float): Sampling frequency in Hz.
        n_samples (int): Total number of samples in the original signal.
        t_stft (np.ndarray): Array of center times for each STFT window.

    Returns:
        tuple: (t_full, reconstructed_signal)
    """
    t_full = np.arange(n_samples) / fs
    reconstructed = np.zeros(n_samples)

    # Each t_stft[i] is the center of a window.
    # Calculate window boundaries (approximate) to assign parameters to samples
    if len(t_stft) > 1:
        dt = t_stft[1] - t_stft[0]
    else:
        dt = n_samples / fs

    for i, t_mid in enumerate(t_stft):
        start_time = t_mid - dt / 2
        end_time = t_mid + dt / 2

        mask = (t_full >= start_time) & (t_full < end_time)
        if np.any(mask):
            freq = prediction.dominant_freq[i]
            amp = prediction.amp[i]
            phi = prediction.phi[i]

            # Simple reconstruction: constant frequency/amplitude/phase per segment
            reconstructed[mask] = amp * np.cos(2 * np.pi * freq * t_full[mask] + phi)

    return t_full, reconstructed


def plot_stft_plotly_reconstruction(args, prediction, b_sampled, fs, t_stft):
    """Plots the original signal vs the STFT-reconstructed signal using Plotly."""
    unit, order = set_unit(b_sampled)
    t_full, reconstructed = reconstruct_stft_signal(
        prediction, fs, len(b_sampled), t_stft
    )

    def Scatter(**kwargs):
        if args.render == "dynamic":
            return go.Scatter(kwargs)
        else:
            return go.Scattergl(kwargs)

    fig = go.Figure()

    # Original signal
    fig.add_trace(
        Scatter(
            x=t_full,
            y=b_sampled * order,
            mode="lines",
            name="Original Signal",
            line={"color": "rgba(0,150,250, 0.5)", "shape": "hv"},
            fill="tozeroy",
        )
    )

    # Reconstructed signal
    fig.add_trace(
        Scatter(
            x=t_full,
            y=reconstructed * order,
            mode="lines",
            name="STFT Reconstructed (Dominant)",
            line={"color": "rgb(70,220,70)", "shape": "hv"},
        )
    )

    fig.update_layout(
        title="STFT Time-Varying Reconstruction",
        xaxis_title="Time (s)",
        yaxis_title=f"Bandwidth ({unit})",
        template="plotly",
    )

    return format_plot(fig)


def plot_stft_matplotlib_reconstruction(args, prediction, b_sampled, fs, t_stft):
    """Plots the original signal vs the STFT-reconstructed signal using Matplotlib."""
    unit, order = set_unit(b_sampled)
    t_full, reconstructed = reconstruct_stft_signal(
        prediction, fs, len(b_sampled), t_stft
    )

    fig = plt.figure(figsize=(10, 4))
    plt.fill_between(
        t_full,
        0,
        b_sampled * order,
        label="Original signal",
        alpha=0.5,
        step="post",
        color="royalblue",
    )
    plt.plot(t_full, b_sampled * order, drawstyle="steps-post", color="royalblue")

    plt.plot(
        t_full,
        reconstructed * order,
        label="STFT Reconstructed",
        color="limegreen",
        drawstyle="steps-post",
    )

    plt.title("STFT Time-Varying Reconstruction")
    plt.ylabel(f"Bandwidth ({unit})")
    plt.xlabel("Time (s)")
    plt.legend()
    plt.grid(True)
    return fig


def plot_stft_plotly_dominant_freq(args, prediction, b_sampled, fs, t_stft):
    """
    Plots the dominant frequency tracking over time using Plotly.
    Includes a secondary axis for period (T=1/f).
    """

    def Scatter(**kwargs):
        if args.render == "dynamic":
            return go.Scatter(kwargs)
        else:
            return go.Scattergl(kwargs)

    fig = go.Figure()

    # Calculate periods for hover info and secondary axis
    periods = np.zeros_like(prediction.dominant_freq)
    mask = prediction.dominant_freq > 0
    periods[mask] = 1.0 / prediction.dominant_freq[mask]

    # Dominant Frequency (primary axis)
    fig.add_trace(
        Scatter(
            x=t_stft,
            y=prediction.dominant_freq,
            mode="lines+markers",
            name="Dominant Frequency",
            line={"color": "rgb(220,50,50)"},
            marker={"size": 6},
            hovertemplate="<b>Time</b>: %{x:.2f} s"
            + "<br><b>Freq</b>: %{y:.3e} Hz"
            + "<br><b>T</b>: %{customdata:.3f} s",
            customdata=periods,
            yaxis="y1",
        )
    )

    # Period (secondary axis, visible only in legend/hover)
    fig.add_trace(
        Scatter(
            x=t_stft,
            y=periods,
            mode="markers",
            name="Period (s)",
            visible="legendonly",
            marker={"color": "rgb(50,200,50)"},
            yaxis="y2",
        )
    )

    fig.update_layout(
        title="Dominant Frequency in Each STFT Window",
        xaxis_title="Time (s)",
        yaxis={
            "title": {"text": "Frequency (Hz)", "font": {"color": "rgb(220,50,50)"}},
            "tickfont": {"color": "rgb(220,50,50)"},
        },
        yaxis2={
            "title": {"text": "Period (s)", "font": {"color": "rgb(50,200,50)"}},
            "tickfont": {"color": "rgb(50,200,50)"},
            "anchor": "x",
            "overlaying": "y",
            "side": "right",
        },
        showlegend=True,
        template="plotly",
    )

    return format_plot(fig)


def plot_stft_matplotlib_dominant_freq(args, prediction, b_sampled, fs, t_stft):
    """
    Plots the dominant frequency tracking over time using Matplotlib.
    Includes a secondary axis for period (T=1/f).
    """
    fig, ax1 = plt.subplots(figsize=(12, 4))

    ax1.plot(
        t_stft, prediction.dominant_freq, "r-o", label="Dominant Frequency", markersize=4
    )
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Frequency (Hz)", color="red")
    ax1.tick_params(axis="y", labelcolor="red")

    # Add secondary axis for Period
    ax2 = ax1.twinx()
    periods = np.zeros_like(prediction.dominant_freq)
    mask = prediction.dominant_freq > 0
    periods[mask] = 1.0 / prediction.dominant_freq[mask]

    ax2.set_ylabel("Period (s)", color="green")
    ax2.tick_params(axis="y", labelcolor="green")
    ax2.plot(t_stft, periods, "g--", label="Period", alpha=0.5)

    fig.suptitle("Dominant Frequency in Each STFT Window")
    ax1.grid(True)
    # Put legend outside to match sizing of other figures
    ax1.legend(loc="upper left")
    fig.tight_layout()
    return fig
