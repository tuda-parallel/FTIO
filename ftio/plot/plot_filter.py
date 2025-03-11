import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ftio.freq._dft import  compute_dft_spectrum



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
    axs[0].plot(t, filtered_signal, label='Filtered Signal', linestyle='-', marker='x')
    axs[0].set_title("Time-Domain Signal")
    axs[0].set_xlabel("Time [s]")
    axs[0].set_ylabel("Amplitude")
    axs[0].legend(loc='best')

    # Frequency response plot (Magnitude Response)
    axs[1].bar(freqs, amp, width=0.05, color='green', alpha=0.6, label="Original")
    axs[1].bar(freqs, amp_filtered, width=0.05, color='red', alpha=0.6, label="Filtered")
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
    amp, _, freqs = compute_dft_spectrum(b,args.freq)
    amp_filtered, _, _ = compute_dft_spectrum(filtered_signal,args.freq)

    #compute the time:
    t =  1 / args.freq * np.arange(0, len(b))

    # Create a subplot figure with 2 rows and 1 column
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Time-Domain Signal", "Frequency Response"),
        vertical_spacing=0.15,
        shared_xaxes=False,
        row_heights=[0.45, 0.55],
    )

    # Time-domain signal plot (Original vs Filtered)
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

    # Magnitude Response Plot
    fig.add_trace(
        go.Bar(
            x=freqs,
            y=amp,
            name="Original",
            marker=dict(color="green"),
            # opacity=0.3,  
        ),
        row=2,
        col=1,
    )

    # Phase Response Plot
    fig.add_trace(
        go.Bar(
            x=freqs,
            y=amp_filtered,
            name="Filtered",
            marker=dict(color="red"),
            # opacity=0.3,  
        ),
        row=2,
        col=1,
    )

    # Update layout for the figure
    fig.update_layout(
        title=f"Filtered Signal ({args.filter_type} filter)",
        xaxis_title="Time [s]",
        yaxis_title="Amplitude",
        showlegend=True,
    )

    fig.update_xaxes(title_text="Frequency [Hz]", row=2, col=1)
    fig.update_yaxes(title_text="Amplitude", row=2, col=1)
    fig.update_yaxes(title_text="Amplitude", row=1, col=1)

    fig.show()


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
