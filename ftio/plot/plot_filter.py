import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ftio.freq._dft import compute_dft_spectrum


def plot_filter_results_matplotlib(args, b, filtered_signal):
    """
    Plots the time-domain signal (Original vs Filtered) and Bode plot (Magnitude and Phase) using Matplotlib.

    Parameters:
    - args: Namespace containing filter parameters.
    - b: np.ndarray, original signal.
    - filtered_signal: np.ndarray, the filtered signal.
    """
    # Compute the DFT of the filtered signal
    amp, _, freqs = compute_dft_spectrum(b, args.freq)
    amp_filtered, _, _ = compute_dft_spectrum(filtered_signal, args.freq)

    # Compute the time axis
    t = 1 / args.freq * np.arange(0, len(b))

    # Create a figure with two subplots (1 row, 2 columns)
    fig, axs = plt.subplots(2, 1, figsize=(10, 8), sharex=False)

    # Time-domain signal plot (Original vs Filtered)
    axs[0].plot(t, b, label="Original Signal", linestyle="-", marker="o")
    axs[0].plot(t, filtered_signal, label="Filtered Signal", linestyle="-", marker=".")
    axs[0].set_title("Time-Domain Signal")
    axs[0].set_xlabel("Time (s)", fontsize=17)
    axs[0].set_ylabel("Amplitude", fontsize=17)
    axs[0].grid(True, which="both", linestyle="--", alpha=0.6)
    axs[0].ticklabel_format(axis="y", style="sci", scilimits=(-5, 3))
    axs[0].ticklabel_format(axis="x", style="sci", scilimits=(-5, 3))
    axs[0].tick_params(axis="both", labelsize=12)
    plt.xlim(t[0], t[-1])
    axs[0].legend(loc="upper right")

    # Frequency response plot (Magnitude Response)
    step = args.freq / (2 * len(freqs))
    axs[1].bar(freqs, amp, width=step, color="green", alpha=0.6, label="Original")
    axs[1].bar(
        freqs,
        amp_filtered,
        width=step,
        color="red",
        alpha=0.6,
        label="Filtered",
    )
    axs[1].set_title("Frequency Response")
    axs[1].set_xlabel("Time (s)", fontsize=17)
    axs[1].set_ylabel("Frequency (Hz)", fontsize=17)
    axs[1].grid(True, which="both", linestyle="--", alpha=0.6)
    axs[1].ticklabel_format(axis="y", style="sci", scilimits=(-5, 3))
    axs[1].ticklabel_format(axis="x", style="sci", scilimits=(-5, 3))
    axs[1].tick_params(axis="both", labelsize=12)
    plt.xlim(freqs[0], freqs[-1])
    axs[1].legend(loc="upper right")

    # Adjust layout to prevent overlap
    plt.tight_layout()
    plt.suptitle(f"Filtered Signal ({args.filter_type} filter)", fontsize=16)
    plt.subplots_adjust(top=0.92)

    # Show the plot
    return [fig]


def plot_filter_results_plotly(args, b, filtered_signal, as_subplots=True):
    """
    Plots the time-domain signal (Original vs Filtered) and Bode plot (Magnitude and Phase).

    Parameters:
    - args: Namespace containing filter parameters.
    - b: np.ndarray, original signal.
    - filtered_signal: np.ndarray, the filtered signal.
    - as_subplots: bool, if True (default), plots as a single figure with subplots;
                   if False, displays two separate figures.
    """
    # Compute the DFT of the signals
    amp, _, freqs = compute_dft_spectrum(b, args.freq)
    amp_filtered, _, _ = compute_dft_spectrum(filtered_signal, args.freq)

    # Compute the time vector
    t = 1 / args.freq * np.arange(0, len(b))

    if as_subplots:
        # Create subplots: Time-Domain (row 1), Frequency-Domain (row 2)
        fig = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=("Time-Domain Signal", "Magnitude Response"),
            sharedx=False,
        )

        # Time-Domain traces
        fig.add_trace(
            go.Scatter(
                x=t,
                y=b,
                mode="lines+markers",
                line={"shape": "hv"},
                name="Original Signal",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=t,
                y=filtered_signal,
                mode="lines+markers",
                line={"shape": "hv"},
                name="Filtered Signal",
            ),
            row=1,
            col=1,
        )

        # Frequency-Domain traces
        fig.add_trace(
            go.Bar(x=freqs, y=amp, name="Original", marker=dict(color="green")),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=freqs,
                y=amp_filtered,
                name="Filtered",
                marker=dict(color="red"),
            ),
            row=2,
            col=1,
        )

        # Layout settings
        fig.update_layout(
            height=800,
            title_text="Filter Analysis: Time and Frequency Domain",
            xaxis=dict(title="Time [s]"),
            yaxis=dict(title="Amplitude"),
            xaxis2=dict(title="Frequency [Hz]"),
            yaxis2=dict(title="Amplitude"),
            showlegend=True,
        )
        fig = [fig]
    else:
        fig = []
        # Separate Time-Domain figure
        fig_time = go.Figure()
        fig_time.add_trace(
            go.Scatter(
                x=t,
                y=b,
                mode="lines+markers",
                line={"shape": "hv"},
                name="Original Signal",
            )
        )
        fig_time.add_trace(
            go.Scatter(
                x=t,
                y=filtered_signal,
                mode="lines+markers",
                line={"shape": "hv"},
                name="Filtered Signal",
            )
        )
        fig_time.update_layout(
            title="Time-Domain Signal",
            xaxis_title="Time [s]",
            yaxis_title="Amplitude",
            showlegend=True,
        )

        # Separate Frequency-Domain figure
        fig_freq = go.Figure()
        fig_freq.add_trace(
            go.Bar(x=freqs, y=amp, name="Original", marker=dict(color="green"))
        )
        fig_freq.add_trace(
            go.Bar(
                x=freqs,
                y=amp_filtered,
                name="Filtered",
                marker=dict(color="red"),
            )
        )
        fig_freq.update_layout(
            title="Magnitude Response",
            xaxis_title="Frequency [Hz]",
            yaxis_title="Amplitude",
            showlegend=True,
        )

        fig = [fig_time, fig_freq]

    return fig


def plot_filter_results(args, b, filtered_signal) -> list:
    """
    Selects the appropriate plotting function based on `args.engine` ('mat' for matplotlib, 'plotly' for Plotly).

    Parameters:
    - args: Namespace containing filter parameters, including engine selection ('mat' or 'plotly').
    - b: np.ndarray, original signal.
    - filtered_signal: np.ndarray, the filtered signal.

    Returns:
        list of figures
    """
    if "plot" in args.engine:
        # Use Plotly function
        fig = plot_filter_results_plotly(args, b, filtered_signal)
    elif "mat" in args.engine:
        # Use Matplotlib function
        fig = plot_filter_results_matplotlib(args, b, filtered_signal)
    else:
        fig = []

    return fig
