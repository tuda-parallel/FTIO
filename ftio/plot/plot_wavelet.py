""" Wavelet plot methods 
"""

import numpy as np
import pywt
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from argparse import Namespace


####################################################################################################
# Deprecated functions
####################################################################################################


def plot_wave_cont(
    b_sampled: np.ndarray,
    frequencies: np.ndarray,
    freq: float,
    t: np.ndarray,
    coefficients: np.ndarray,
) -> plt.Figure:
    """
    Plot continuous wavelet transform.

    Args:
        b_sampled (np.ndarray): Sampled signal.
        frequencies (np.ndarray): Frequencies array.
        freq (float): Sampling frequency.
        t (np.ndarray): Time array.
        coefficients (np.ndarray): Wavelet coefficients.

    Returns:
        plt.Figure: Matplotlib figure object.
    """
    time_disc = t[0] + 1 / freq * np.arange(0, len(b_sampled))
    power = (
        abs(coefficients)
    ) ** 2  # probably error on https://ataspinar.com/2018/12/21/a-guide-for-using-the-wavelet-transform-in-machine-learning/
    counter = 0
    for i in range(
        1, len(coefficients)
    ):  # see Continuous wavelet transform properties @ https://en.wikipedia.org/wiki/Continuous_wavelet_transform
        power[counter] = 1 / i * power[counter]
        counter = counter + 1
    fig, ax = plt.subplots(figsize=(12, 4))
    im = ax.contourf(
        time_disc,
        frequencies,
        power,
        np.arange(0, power.max(), power.max() / 10),
        extend="neither",
        cmap=plt.cm.seismic,
    )
    # fig.colorbar(im, cax=cbar_ax, orientation="vertical")
    fig.colorbar(im, ax=ax)
    ax.set_ylabel("Frequency (Hz)", fontsize=18)
    ax.set_xlabel("Time (s)", fontsize=18)
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)
    fig.tight_layout()
    plt.show()
    return fig


def plot_wave_disc(
    b_sampled: np.ndarray,
    coffs,
    t: np.ndarray,
    freq: float,
    level: int,
    wavelet: str,
    b: np.ndarray,
) :
    """
    Plot discrete wavelet transform.

    Args:
        b_sampled (np.ndarray): Sampled signal.
        coffs: Wavelet coefficients.
        t (np.ndarray): Time array.
        freq (float): Sampling frequency.
        level (int): Decomposition level.
        wavelet (str): Wavelet type.
        b (np.ndarray): Original signal.

    Returns:
        Tuple[np.ndarray, List[plt.Figure]]: Coefficients and list of Matplotlib figure objects.
    """
    n = len(b_sampled)
    time_disc = t[0] + 1 / freq * np.arange(0, n)
    reconstructed_signal = pywt.waverec(coffs, wavelet, "smooth")
    f = []
    f1 = plt.figure(figsize=(12, 4))
    plt.plot(t, b, label="signal")
    plt.plot(
        time_disc,
        reconstructed_signal[0 : len(time_disc)],
        label="reconstructed levels %d" % level,
        linestyle="--",
    )
    # plt.plot(time,reconstructed_signal[0:len(time)], label="reconstructed levels %d", linestyle="--")
    plt.legend(loc="upper right")
    plt.title("single reconstruction", fontsize=20)
    plt.xlabel("time axis", fontsize=16)
    plt.ylabel("Amplitude", fontsize=16)

    # ? use recon or coffs to either create the paritallly reconstructed signal or the cofficent of the DTW:
    # ? recon -> idea is that all values are extracted just before reconstructing the signal. This adds less resolution to the upper frequencies
    # ? x ---->.g -->↓ 2 --> C1 --> ↑2 -->* g-1  #   captuere   # -->+ --> x
    # ?     "->.h -->↓ 2 --> C2 --> ↑2 -->* h-1  #      here    #  --^
    use = "recon"
    # use = "coffs" #hold the signal, not upsample!
    cc = np.zeros((level + 1, n))
    for i in np.arange(start=level, stop=0, step=-1):
        # coffs ->  [cA_n, cD_n, cD_n-1, …, cD2, cD1]
        # reconstruction by 1) upsampling and 2) multiplying with the appropiate filter
        # page 29 on https://www.corsi.univr.it/documenti/OccorrenzaIns/matdid/matdid358630.pdf
        # GoH0+G1H1 = 1 -> Multiply a with H1 and d with G1
        # https://medium.com/@shouke.wei/process-of-discrete-wavelet-transform-iii-wavelet-partial-reconstruction-ca7a8f9420dc
        if "recon" in use:
            cc[level - i + 1] = pywt.upcoef(
                "d", coffs[level - i + 1], wavelet, level=i
            )[:n]
        else:
            # Wrong: only upsample: ‘↑ 2’ denotes ‘upsample by 2’ (put 0’s before values)
            # cc[level-i+1,::2**(i)] = coffs[level-i+1]
            # Correct: upsample is used for reconstruction, we only want to visualize -> hold the data constatnt during sample step

            counter = 0
            for j in range(0, n):
                if j % 2**i == 0:
                    cc[level - i + 1, j] = coffs[level - i + 1][counter]
                    counter = counter + 1
                else:
                    cc[level - i + 1, j] = cc[level - i + 1, j - 1]

    if "recon" in use:
        cc[0] = pywt.upcoef("a", coffs[0], wavelet, level=level)[:n]
        fig, ax = plt.subplots(nrows=level + 2, ncols=1, figsize=(12, 12))
        ax[0].plot(t, b, label="signal")
        for i in range(0, level + 1):
            if i == 0:
                sum = cc[0]
            else:
                sum = sum + cc[i]
        ax[0].plot(time_disc, sum, label="sum")
        for i in np.arange(start=level, stop=0, step=-1):
            ax[level - i + 2].plot(time_disc, cc[level - i + 1])
            ax[level - i + 2].set_title(
                f"reconstruction at level {i} from detailed coff -> [{freq / 2 ** (i + 1)}, {freq / 2**i}] Hz"
            )
        ax[1].plot(time_disc, cc[0])
        ax[1].set_title(
            f"reconstruction at level {level} from approximated coff -> [0, {freq / 2 ** (level + 1)}] Hz"
        )
        fig.legend()
        fig.tight_layout()
        f.append(fig)

    else:
        counter = 0
        for j in range(0, n):
            if j % 2**level == 0:
                cc[0, j] = coffs[0][counter]
                counter = counter + 1
            else:
                cc[0, j] = cc[0, j - 1]

    # Use freq or level to plot either the frequency or the level in the y-axis
    show = "freq"
    f_2 = plt.figure(figsize=(12, 4))
    plt.xlabel("Time (s)", fontsize=18)
    # plt.title("Discrete Wavelet Transform with %d decompositions"%level)
    if "freq" in show:
        plt.ylabel("Frequency (Hz)", fontsize=18)
        plt.xticks(fontsize=18)
        plt.yticks(fontsize=18)
        y = np.concatenate(
            [np.array([0]), freq / 2 ** np.arange(start=level + 1, stop=0, step=-1)]
        )
        x = (
            -2 / freq + t[0] + 1 / freq * np.arange(0, len(b_sampled) + 1)
        )  # ? add corner shifted by half a sample step
        X, Y = np.meshgrid(x, y)
        # plt.pcolormesh(X, Y,abs(cc),cmap=plt.cm.coolwarm,shading="flat")
        plt.pcolormesh(X, Y, abs(cc), cmap=plt.cm.seismic, shading="flat")
    else:
        y = np.arange(start=level, stop=-1, step=-1)
        x = t[0] + 1 / freq * np.arange(0, len(b_sampled))
        X, Y = np.meshgrid(x, y)
        plt.pcolormesh(X, Y, abs(cc), cmap=plt.cm.coolwarm)
        plt.ylabel("decomposition level")
        # cc = np.flip(cc,0)
        plt.gca().invert_yaxis()

    # plt.pcolormesh(X, Y, cc,cmap=plt.cm.seismic)
    # plt.pcolormesh(X, Y,abs(cc),cmap=plt.cm.seismic,shading="flat")
    # plt.plot(X.flat, Y.flat, "x", color="m")
    plt.colorbar()
    f.append(f_2)
    plt.tight_layout()
    f.append(f1)
    return cc, f


####################################################################################################
# Matplotlib plotting functions
####################################################################################################
def matplot_spectrum(
    t: np.ndarray,
    power: np.ndarray,
    label: str = None,
    peaks: np.ndarray = None,
    subplot=[],
) -> plt.Figure:
    """
    Plot wavelet power spectrum using Matplotlib.

    Args:
        t (np.ndarray): Time array.
        power (np.ndarray): Power array.
        label (str): Label for the plot.
        peaks (np.ndarray): Detected peaks.
        subplot: Subplot configuration.

    Returns:
        plt.Figure: Matplotlib figure object.
    """
    if subplot:
        fig = plt.subplot(subplot[0], subplot[1], subplot[2])
    else:
        fig = plt.figure(figsize=(12, 4))

    plt.plot(
        t,
        power,
        label=f"Power at Dominant Scale {label if label else ''}",
        color="orange",
    )
    if peaks is not None:
        plt.scatter(t[peaks], power[peaks], color="red", label="Detected Peaks")
    plt.title("Wavelet Power at Dominant Scale")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Power")
    plt.legend()
    plt.grid()
    plt.tight_layout()

    return fig


def matplot_wave_cont(
    t: np.ndarray,
    power_spectrum: np.ndarray,
    frequencies: np.ndarray,
    subplot=[],
) -> plt.Figure:
    """
    Plot wavelet power spectrum using Matplotlib.

    Args:
        t (np.ndarray): Time array.
        power_spectrum (np.ndarray): Power spectrum array.
        frequencies (np.ndarray): Frequencies array.
        subplot: Subplot configuration.

    Returns:
        plt.Figure: Matplotlib figure object.
    """
    if subplot:
        fig = plt.subplot(subplot[0], subplot[1], subplot[2])
    else:
        fig = plt.figure(figsize=(12, 4))

    # plt.imshow(power_spectrum, aspect='auto', extent=[t[0], t[-1], scales[-1], scales[0]], cmap='viridis')
    plt.imshow(
        power_spectrum,
        aspect="auto",
        cmap="viridis",
        extent=[t[0], t[-1], frequencies[0], frequencies[-1]],
    )
    plt.colorbar(label="Power")
    plt.title("Wavelet Power Spectrum (All Scales)")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Frequencies (Hz)")
    plt.grid()

    return fig


def matplot_wave_cont_and_spectrum(
    t: np.ndarray,
    frequencies: np.ndarray,
    power_spectrum: np.ndarray,
    dominant_power_spectrum: np.ndarray,
    label: str = None,
    peaks: np.ndarray = None,
) -> plt.Figure:
    """
    Plot continuous wavelet transform and power spectrum using Matplotlib.

    Args:
        t (np.ndarray): Time array.
        frequencies (np.ndarray): Frequencies array.
        power_spectrum (np.ndarray): Power spectrum array.
        dominant_power_spectrum (np.ndarray): Dominant power spectrum array.
        label (str): Label for the plot.
        peaks (np.ndarray): Detected peaks.

    Returns:
        plt.Figure: Matplotlib figure object.
    """
    fig = plt.figure(figsize=(16, 12))
    matplot_wave_cont(t, power_spectrum, frequencies, [2, 1, 1])
    matplot_spectrum(t, dominant_power_spectrum, label, peaks, [2, 1, 2])

    return fig


def matplot_plot_scales(
    t: np.ndarray,
    b: np.ndarray,
    power_spectrum: np.ndarray,
    frequencies: np.ndarray,
    scales: np.ndarray,
    common_xaxis: bool = True,
) -> plt.Figure:
    """
    Plot wavelet power spectrum at different scales using Matplotlib.

    Args:
        t (np.ndarray): Time array.
        b (np.ndarray): Original signal.
        power_spectrum (np.ndarray): Power spectrum array (shape: [num_scales, num_time_points]).
        frequencies (np.ndarray): Frequencies array.
        scales (np.ndarray): Scale array matching the frequencies.
        common_xaxis (bool): If True, enables a common x-axis for zooming.

    Returns:
        plt.Figure: Matplotlib figure object.
    """

    # Ensure power_spectrum is a 2D array (scales, time)
    if len(power_spectrum.shape) != 2:
        raise ValueError("Power spectrum must be a 2D array (scales, time)")

    # Set up the figure and subplots
    fig, axes = plt.subplots(len(scales) + 2, 1, figsize=(10, 6), sharex=common_xaxis)
    axes = axes.flatten()

    # Plot the time series on the first subplot
    axes[0].plot(t, b, color="blue", label="Time Series")
    axes[0].set_ylabel("Amplitude")
    axes[0].set_title("Bandwidth over Time")
    axes[0].legend()

    # Plot the wavelet power spectrum (all scales)
    # Make sure the power_spectrum has the correct shape: [num_scales, num_time_points]
    axes[1].imshow(power_spectrum, aspect='auto', extent=[t[0], t[-1], frequencies[-1], frequencies[0]], cmap='jet')
    axes[1].set_xlabel("Time")
    axes[1].set_ylabel("Frequency")
    axes[1].set_title("Wavelet Power Spectrum (All Scales)")
    
    # Plot the power spectrum at each scale
    for i, scale in enumerate(scales):
        axes[i + 2].plot(t, power_spectrum[i, :], label=f"Scale {scale} (Frequency {frequencies[i]:.3f})")
        axes[i + 2].set_xlabel("Time")
        axes[i + 2].set_ylabel("Power")
        axes[i + 2].legend()
        axes[i + 2].set_title(f"Power at Scale {scale} (Frequency {frequencies[i]:.3f})")

    # Adjust layout to avoid overlapping
    # plt.tight_layout()

    return fig


####################################################################################################
# Plotly plotting functions
####################################################################################################
def plotly_spectrum(
    t: np.ndarray,
    power: np.ndarray,
    label: str = None,
    peaks: np.ndarray = None,
    subplot=None,
    fig: go.Figure = None,
) -> go.Figure:
    """
    Plot wavelet power spectrum using Plotly.

    Args:
        t (np.ndarray): Time array.
        power (np.ndarray): Power array.
        label (str): Label for the plot.
        peaks (np.ndarray): Detected peaks.
        subplot: Subplot configuration.
        fig (go.Figure): Plotly figure object.

    Returns:
        go.Figure: Plotly figure object.
    """
    if fig is None:
        fig = go.Figure()

    trace = go.Scatter(
        x=t,
        y=power,
        mode="lines",
        name=f"Power at {label if label else 'Dominant Scale'}",
        line=dict(color="orange"),
    )
    if subplot:
        fig.add_trace(trace, row=subplot[0], col=subplot[1])
    else:
        fig.add_trace(trace)

    if peaks is not None:
        peak_trace = go.Scatter(
            x=t[peaks],
            y=power[peaks],
            mode="markers",
            marker=dict(color="red"),
            name="Detected Peaks",
        )

        if subplot:
            fig.add_trace(peak_trace, row=subplot[0], col=subplot[1])
        else:
            fig.add_trace(peak_trace)

    if subplot:
        fig.update_xaxes(title_text="Time (seconds)", row=subplot[0], col=subplot[1])
        fig.update_yaxes(title_text="Power", row=subplot[0], col=subplot[1])
    else:
        fig.update_layout(
            title=f"Wavelet Power at {label if label else 'Dominant Scale'}",
            xaxis_title="Time (seconds)",
            yaxis_title="Power",
        )

    return fig


def plotly_wave_cont(
    t: np.ndarray,
    frequencies: np.ndarray,
    power_spectrum: np.ndarray,
    subplot=None,
    fig: go.Figure = None,
) -> go.Figure:
    """
    Plots a wavelet power spectrum using Plotly.

    Args:
        t (np.ndarray): Array of time values.
        frequencies (np.ndarray): Array of frequency values.
        power_spectrum (np.ndarray): 2D array of power spectrum values.
        subplot (tuple, optional): Tuple specifying the subplot position (row, col). Defaults to None.
        fig (go.Figure, optional): Existing Plotly figure to add the heatmap to. Defaults to None.

    Returns:
        go.Figure: The Plotly figure object with the wavelet power spectrum heatmap.
    """
    if fig is None:
        fig = go.Figure()

    heatmap = go.Heatmap(x=t, y=frequencies, z=power_spectrum, colorscale="viridis")
    if subplot:
        fig.add_trace(heatmap, row=subplot[0], col=subplot[1]) 
        fig.update_xaxes(title_text="Time (seconds)", row=subplot[0], col=subplot[1])
        fig.update_yaxes(title_text="Frequencies (Hz)", row=subplot[0], col=subplot[1])
    else:
        fig.add_trace(heatmap)
        fig.update_layout(
            title=f"Scaleogram",
            xaxis_title="Time (seconds)",
            yaxis_title="Frequencies (Hz)",
        )

    return fig


def plotly_wave_cont_and_spectrum(
    t: np.ndarray,
    frequencies: np.ndarray,
    power_spectrum: np.ndarray,
    dominant_power_spectrum: np.ndarray,
    label: str = None,
    peaks: np.ndarray = None,
) -> go.Figure:
    """
    Plot continuous wavelet transform and power spectrum using Plotly.

    Args:
        t (np.ndarray): Time array.
        f (np.ndarray): frequencies array.
        power_spectrum (np.ndarray): Power spectrum array.
        dominant_power_spectrum (np.ndarray): Dominant power spectrum array.
        label (str): Label for the plot.
        peaks (np.ndarray): Detected peaks.

    Returns:
        go.Figure: Plotly figure object.
    """
    rows = 2
    fig = make_subplots(
        rows=rows,
        cols=1,
        subplot_titles=[
            "Wavelet Power Spectrum (All Scales)",
            "Wavelet Power at Dominant Scale",
        ],
        vertical_spacing=0.2,
        shared_xaxes=True,
    )

    fig = plotly_wave_cont(t, frequencies, power_spectrum, subplot=[1, 1], fig=fig)
    fig = plotly_spectrum(
        t, dominant_power_spectrum, label, peaks, subplot=[2, 1], fig=fig
    )

    for i in range(1, rows):
        fig.update_xaxes(showticklabels=True, row=i, col=1)
        fig.update_xaxes(title_text="Time (seconds)", row=i, col=1)
        fig.update_yaxes(title_text="Power", row=i, col=1)

    fig.update_layout(height=1200, width=1600, showlegend=True)

    return fig


def plotly_plot_scales(
    t: np.ndarray,
    b: np.ndarray,
    power_spectrum: np.ndarray,
    frequencies: np.ndarray,
    scales: np.ndarray,
    common_xaxis: bool = True,
) -> go.Figure:
    """
    Plot wavelet power spectrum at different scales using Plotly.

    Args:
        t (np.ndarray): Time array.
        b (np.ndarray): Original signal.
        power_spectrum (np.ndarray): Power spectrum array.
        frequencies (np.ndarray): Frequencies array.
        scales (np.ndarray): scale array. matching the frequencies
        common_axis (bool): If True, enables a common x-axis for zooming.

    Returns:
        go.Figure: Plotly figure object.
    """

    names = ["bandwidth over time", "Wavelet Power Spectrum (All Scales)"]
    names.extend(
        [
            f"Power at Scale {scale} (freq. {frequencies[i]:.3f} -- period {1/frequencies[i] if frequencies[i] > 0 else 0:.3f})"
            for i, scale in enumerate(scales)
        ]
    )
    fig = make_subplots(
        rows=len(scales) + 2, cols=1, subplot_titles=names, shared_xaxes=common_xaxis
    )
    fig.add_trace(
        go.Scatter(x=t, y=b, mode="lines", name="Time Series", line=dict(color="blue")),
        row=1,
        col=1,
    )
    fig = plotly_wave_cont(t, frequencies, power_spectrum, subplot=[2, 1], fig=fig)
    for i, scale in enumerate(scales):
        fig = plotly_spectrum(
            t,
            power_spectrum[i, :],
            f"Scale {scale} (Frequency {frequencies[i]:.3f})",
            subplot=[i + 3, 1],
            fig=fig,
        )

    # Adjust layout to allow scrolling and zooming
    for i in range(1, len(scales) + 3):  # 1 to (number of scales + 2)
        fig.update_xaxes(showticklabels=True, row=i, col=1)

    fig.update_layout(
        showlegend=True,
        height=400 * (len(scales) + 2),  # Makes the figure scrollable
        xaxis_title="Time",
        yaxis_title="Amplitude",
    )

    return fig


####################################################################################################
# Plotting functions
####################################################################################################
def plot_wave_cont_and_spectrum(
    args: Namespace,
    t: np.ndarray,
    frequencies: np.ndarray,
    power_spectrum_all_scales: np.ndarray,
    dominant_power_spectrum: np.ndarray,
    label: str = None,
    peaks: np.ndarray = None,
) -> plt.Figure:
    """
    Plot continuous wavelet transform and power spectrum using the specified plotting engine.

    Args:
        args (Namespace): Arguments containing the plotting engine.
        t (np.ndarray): Time array.
        power_spectrum (np.ndarray): Power spectrum array.
        dominant_power_spectrum (np.ndarray): Dominant power spectrum array.
        label (str): Label for the plot.
        peaks (np.ndarray): Detected peaks.

    Returns:
        plt.Figure: Matplotlib or Plotly figure object.
    """
    if "plotly" in args.engine:
        fig = plotly_wave_cont_and_spectrum(
            t,
            frequencies,
            power_spectrum_all_scales,
            dominant_power_spectrum,
            label,
            peaks,
        )
    else:
        fig = matplot_wave_cont_and_spectrum(
            t,
            frequencies,
            power_spectrum_all_scales,
            dominant_power_spectrum,
            label,
            peaks,
        )

    return fig


def plot_spectrum(
    args: Namespace,
    t: np.ndarray,
    power_spectrum: np.ndarray,
    label: str = None,
    peaks: np.ndarray = None,
) -> plt.Figure:
    """
    Plot wavelet power spectrum using the specified plotting engine.

    Args:
        args (Namespace): Arguments containing the plotting engine.
        t (np.ndarray): Time array.
        power_spectrum (np.ndarray): Power spectrum array for a specific scale.
        label (str): Label for the plot.
        peaks (np.ndarray): Detected peaks.

    Returns:
        plt.Figure: Matplotlib or Plotly figure object.
    """
    if "plotly" in args.engine:
        fig = plotly_spectrum(t, power_spectrum, label, peaks)
    else:
        fig = matplot_spectrum(t, power_spectrum, label, peaks)

    return fig


def plot_scales(
    args, 
    t: np.ndarray,
    b: np.ndarray,
    power_spectrum: np.ndarray,
    frequencies: np.ndarray,
    scales: np.ndarray,
    common_xaxis: bool = True,
) -> plt.Figure:
    """
    Plots the wavelet scales using either Plotly or Matplotlib based on the specified engine.

    Args:
        args (Namespace): Arguments containing the plotting engine information.
        t (np.ndarray): Time array.
        b (np.ndarray): Data array.
        power_spectrum (np.ndarray): Power spectrum array.
        frequencies (np.ndarray): Frequencies array.
        scales (np.ndarray): Scales array.
        common_xaxis (bool, optional): Whether to use a common x-axis for the plots. Defaults to True.

    Returns:
        plt.Figure: Matplotlib or Plotly figure object.
    """
    if "plotly" in args.engine:
        fig = plotly_plot_scales(t, b, power_spectrum, frequencies, scales, common_xaxis)
    else:
        fig = matplot_plot_scales(t, b, power_spectrum, frequencies, scales, common_xaxis)

    return fig
