import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ftio.freq._dft import  compute_dft_spectrum
from ftio.freq.freq_html import create_html



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
    axs[0].plot(t, b, label='Original Signal', linestyle='-', marker='o')
    axs[0].plot(t, filtered_signal, label='Filtered Signal', linestyle='-', marker='.')
    axs[0].set_title("Time-Domain Signal")
    axs[0].set_xlabel("Time [s]")
    axs[0].set_ylabel("Amplitude")
    axs[0].legend(loc='best')

    # Frequency response plot (Magnitude Response)
    step = args.freq / (2 * len(freqs))
    axs[1].bar(freqs, amp, width=step, color='green', alpha=0.6, label="Original")
    axs[1].bar(freqs, amp_filtered, width=step, color='red', alpha=0.6, label="Filtered")
    axs[1].set_title("Frequency Response")
    axs[1].set_xlabel("Frequency [Hz]")
    axs[1].set_ylabel("Amplitude")
    axs[1].legend(loc='best')

    # Adjust layout to prevent overlap
    plt.tight_layout()
    plt.suptitle(f"Filtered Signal ({args.filter_type} filter)", fontsize=16)
    plt.subplots_adjust(top=0.92)

    # Show the plot
    plt.show()


def plot_filter_results_plotly(args, b, filtered_signal):
    """
    Plots the time-domain signal (Original vs Filtered) and Bode plot (Magnitude and Phase).

    Parameters:
    - args: Namespace containing filter parameters.
    - b: np.ndarray, original signal.
    - filtered_signal: np.ndarray, the filtered signal.
    """
    # Compute the DFT of the filtered signal
    amp, _, freqs = compute_dft_spectrum(b, args.freq)
    amp_filtered, _, _ = compute_dft_spectrum(filtered_signal, args.freq)

    # Compute the time:
    t = 1 / args.freq * np.arange(0, len(b))

    # Create list of figures
    figs = []

    # Time-domain signal plot (Original vs Filtered)
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
    figs.append(fig_time)

    # Magnitude Response Plot
    fig_freq = go.Figure()
    fig_freq.add_trace(
        go.Bar(
            x=freqs,
            y=amp,
            name="Original",
            marker=dict(color="green"),
            # marker_line=dict(width=2, color='black')
        )
    )

    fig_freq.add_trace(
        go.Bar(
            x=freqs,
            y=amp_filtered,
            name="Filtered",
            marker=dict(color="red"),
            # marker_line=dict(width=0.2, color='black')
        )
    )    
    fig_freq.update_layout(
        title="Magnitude Response",
        xaxis_title="Frequency [Hz]",
        yaxis_title="Amplitude",
        
    )
    figs.append(fig_freq)

    # Save figures
    plot_name = "filter"
    if "plot_name" in args:
        plot_name += "_" + args.plot_name

    create_html(figs, args.render, {"toImageButtonOptions": {"format": "png", "scale": 4}}, plot_name)


def plot_filter_results(args, b, filtered_signal):
    """
    Selects the appropriate plotting function based on `args.engine` ('mat' for matplotlib, 'plotly' for Plotly).

    Parameters:
    - args: Namespace containing filter parameters, including engine selection ('mat' or 'plotly').
    - b: np.ndarray, original signal.
    - filtered_signal: np.ndarray, the filtered signal.
    """
    if "plot" in args.engine:
        # Use Plotly function
        plot_filter_results_plotly(args, b, filtered_signal)
    elif "mat" in args.engine:
        # Use Matplotlib function
        plot_filter_results_matplotlib(args, b, filtered_signal)
    else:
        pass
