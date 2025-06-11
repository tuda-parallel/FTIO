"""Outlier plot function"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.inspection import DecisionBoundaryDisplay

from ftio.freq.freq_html import create_html
from ftio.plot.helper import format_plot
from ftio.plot.spectrum import plot_both_spectrums


# ?#################################
# ? Plot outliers
# ?#################################
def plot_cepstrum(
    args,
    freq_arr: np.ndarray,
    amp: np.ndarray,
    indecies: np.ndarray,
    conf: np.ndarray,
    dominant_index: np.ndarray,
    d: np.ndarray = np.array([]),
    eps: float = 0,
) -> None:
    """Plots outliers for DB scan

    Args:
        freq_arr (np.ndarray): _description_
        amp (np.ndarray): aplitude or power
        indecies (np.ndarray): _description_
        conf (np.ndarray): _description_
        dominant_index (np.ndarray): _description_
        d (np.ndarray, optional): _description_. Defaults to np.array([]).
    """
    colorscale = [(0, "rgb(0,50,150)"), (0.5, "rgb(150,50,150)"), (1, "rgb(255,50,0)")]
    labels = [(f"cluster {i}") if (i >= 0) else "outliers" for i in dominant_index]
    # prepare figures
    figs = []
    for i in np.arange(0, 4):
        f = go.Figure()
        f = format_plot(f)
        figs.append(f)

    # prepare symbols
    if dominant_index.size > 0 and dominant_index.max() < 20:
        symbol = dominant_index.copy()
        symbol[symbol >= 5] = symbol[symbol >= 5] + 1
        symbol[symbol == -1] = 5  # x marker
        symbol = symbol - 1
    else:
        symbol = np.ones(dominant_index.size)
    labels = np.array(labels)

    if d.size == 0 and len(freq_arr) != 0:
        d = np.vstack(
            (
                freq_arr[indecies] / freq_arr[indecies].max(),
                amp[indecies] / amp[indecies].sum(),
            )
        ).T
    elif len(freq_arr) == 0:
        return
    else:
        pass

    all_colors = [
        px.colors.qualitative.Alphabet[0],
        px.colors.qualitative.Plotly[0],
    ] + px.colors.qualitative.Plotly[2:]
    all_colors = np.array(
        all_colors
        + px.colors.qualitative.Alphabet
        + px.colors.qualitative.Dark24
        + [px.colors.qualitative.Plotly[1]]
    )

    counter = -1
    spec_figs, plt_names = plot_both_spectrums(args, freq_arr, amp, full=False)
    for trace in list(spec_figs.select_traces()):
        counter += 1
        trace.update(marker={"coloraxis": "coloraxis"})
        figs[counter].add_trace(trace)
        if figs[counter].data and "xaxis" in figs[counter].data[0]:
            figs[counter].data[0]["xaxis"] = "x1"
            figs[counter].data[0]["yaxis"] = "y1"

    for i in np.arange(0, 2):
        figs[i].update_layout(coloraxis={"colorscale": colorscale})

    power_spectrum = amp * amp
    powerlog = np.log(power_spectrum + 1e-10)
    # powerlog -= np.mean(powerlog)
    # print (len(powerlog))
    freq_arr_qf = freq_arr * ((len(freq_arr) / 20) / 5)
    cepstrum = np.abs(np.fft.fft(powerlog).real)

    spec_figs, plt_names = plot_both_spectrums(args, freq_arr_qf, cepstrum, full=False)
    for trace in list(spec_figs.select_traces()):
        counter += 1
        trace.update(marker={"coloraxis": "coloraxis"})
        figs[counter].add_trace(trace)
        if figs[counter].data and "xaxis" in figs[counter].data[0]:
            figs[counter].data[0]["xaxis"] = "x1"
            figs[counter].data[0]["yaxis"] = "y1"

    for i in np.arange(2, 4):
        figs[i].update_layout(coloraxis={"colorscale": colorscale})

    y_title = "Power" if args.psd else "Amplitude"
    figs[0].update_xaxes(title_text="Frequency (Hz)")
    figs[0].update_yaxes(title_text=plt_names[0])
    figs[1].update_xaxes(title_text="Frequency (Hz)")
    figs[1].update_yaxes(title_text=plt_names[1])
    figs[2].update_xaxes(title_text="Quefrequency (s)")
    figs[2].update_yaxes(title_text=plt_names[0])
    figs[3].update_xaxes(title_text="Quefrequency (s)")
    figs[3].update_yaxes(title_text=plt_names[1])

    for fig in figs:
        fig.update_layout(width=1300, height=400)
    configuration = {"toImageButtonOptions": {"format": "png", "scale": 4}}
    create_html(figs, args.render, configuration, "cepstrum")


def plot_decision_boundaries(model, d, conf):
    disp = DecisionBoundaryDisplay.from_estimator(
        model,
        d,
        response_method="decision_function",
        alpha=0.5,
    )
    disp.ax_.scatter(d[:, 0], d[:, 1], c=conf, s=20, edgecolor="k")
    disp.ax_.set_title("Binary decision boundary \nof IsolationForest")
    plt.axis("square")
    plt.legend(labels=["outliers", "inliers"], title="true class")
    plt.show()
