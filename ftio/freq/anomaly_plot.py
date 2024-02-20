"""Outlier plot function
"""

from __future__ import annotations
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
from sklearn.inspection import DecisionBoundaryDisplay
from ftio.freq.freq_plot_core import plot_both_spectrums
from ftio.freq.helper import format_plot

# ?#################################
# ? Plot outliers
# ?#################################
def plot_outliers(
    args,
    freq_arr: np.ndarray,
    amp: np.ndarray,
    indecies: np.ndarray,
    conf: np.ndarray,
    dominant_index: np.ndarray,
    d: np.ndarray = np.array([])
) -> None:
    """Plots outliers

    Args:
        freq_arr (np.ndarray): _description_
        amp (np.ndarray): aplitude or power 
        indecies (np.ndarray): _description_
        conf (np.ndarray): _description_
        dominant_index (np.ndarray): _description_
        d (np.ndarray, optional): _description_. Defaults to np.array([]).
    """
    colorscale = ["rgb(0,50,150)", "rgb(150,50,150)", "rgb(255,50,0)"]
    name = "Amplitude"
    if args.psd:
        name = "Power"

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

    names = [(f"cluster {i}") if (i >= 0) else "outliers" for i in dominant_index]
    fig_main = make_subplots(
        rows=4,
        cols=2,
        specs=[
            [{"colspan": 2}, None],
            [{}, {}],
            [{"colspan": 2}, None],
            [{"colspan": 2}, None]
            ],
            horizontal_spacing = 0.2
    )
    
    fig_0 = px.scatter(
        d, x=0, y=1, color=names, labels={"0": "Frequency (Hz)", "1": name}, color_continuous_scale=colorscale
    )
    for trace in list(fig_0.select_traces()):
        fig_main.append_trace(trace, row=1, col=1)
        
    fig_main.update_traces(
        hovertemplate="<b>freq: %{x:.4f}    Hz<br>" + "Amplitude: %{y:.2f}<br>"
    )
    
    
    fig_main.add_trace(
        go.Scatter(
            x=d[:, 0],
            y=d[:, 1],
            mode="markers",
            marker=dict(color=conf,colorscale=colorscale),
            text=conf,
            hovertemplate="<b>Noremed values<br><br>Freq: %{x:.4f}  <br>"
            + "Amplitude: %{y:.2f}<br>"
            + "conf: %{text:.2f}",
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    
    fig_main.add_trace(
        go.Scatter(
            x=freq_arr[indecies],
            y=2*amp[indecies],
            mode="markers",
            marker=dict(color=dominant_index),
            text=dominant_index,
            hovertemplate="<b>Freq: %{x:.4f}    Hz<br>"
            + "Amplitude: %{y:.2f}<br>"
            + "cluster: %{text:.2f}",
            showlegend=False,
        ),
        row=2,
        col=2,
    )


    
    counter = 2
    figs,names = plot_both_spectrums(args,freq_arr, amp, full = False)
    for trace in list(figs.select_traces()):
        counter += 1
        trace.update(marker={'coloraxis': f'coloraxis{counter}'})
        fig_main.append_trace(trace, row=counter, col=1)
    fig_main.update_layout(
    coloraxis3={
        "colorbar": {
            "x": 1,
            "len": .2,
            "y": 0.36,
        },
        "colorscale": colorscale #'Bluered'
    },
    coloraxis4={
        "colorbar": {
            "x": 1,
            "len": .2,
            "y": .09,
        },
        "colorscale": colorscale #'Bluered'
    }
    )
    
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=2, range=[-.01,1.01])
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=2, row=2)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=1, range=[-.01,1.01])
    fig_main.update_yaxes(title_text=f"Normed {name}", col=1, row=2)
    fig_main.update_yaxes(title_text=f"{name}"       , col=2, row=2)
    fig_main.update_yaxes(title_text=f"Normed {name}", col=1, row=1)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=4)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=3)
    fig_main.update_yaxes(title_text=names[0], col=1, row=3)
    fig_main.update_yaxes(title_text=names[1], col=1, row=4)
    fig_main.update_layout(
        width=1300, 
        height=1700, 
        font={"family": "Courier New, monospace", "size": 24, "color": "black"},
        template="plotly",
        )
    format_plot(fig_main)
    fig_main.show()


def plot_dbscan(
    args,
    freq_arr: np.ndarray,
    amp: np.ndarray,
    indecies: np.ndarray,
    conf: np.ndarray,
    dominant_index: np.ndarray,
    eps,
    color,
    d: np.ndarray = np.array([]),
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
    colorscale = ["rgb(0,50,150)", "rgb(150,50,150)", "rgb(255,50,0)"]
    name = "Amplitude"
    if args.psd:
        name = "Power"
    names = [(f"cluster {i}") if (i >= 0) else "outliers" for i in dominant_index]
    fig_main = make_subplots(
        rows=4,
        cols=2,
        specs=[
            [{"colspan": 2}, None],
            [{}, {}],
            [{"colspan": 2}, None],
            [{"colspan": 2}, None]
            ]
    )
    
    fig_main.add_trace(
        go.Scatter(
            x=d[:, 0],
            y=d[:, 1],
            mode="markers",
            marker=dict(color=color,colorscale=colorscale),
            text=names,
            hovertemplate="<b>Noremed values<br><br>Freq: %{x:.4f}  <br>"
            + "Amplitude: %{y:.2f}<br>"
            + "cluster: %{text}",
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    fig_main.update_traces(
        hovertemplate="<b>freq: %{x:.4f}    Hz<br>" + "Amplitude: %{y:.2f}<br>"
    )

    fig_main.add_trace(
        go.Scatter(
            x=d[:, 0],
            y=d[:, 1],
            mode="markers",
            marker=dict(color=color,colorscale=colorscale),
            text=names,
            hovertemplate="<b>Noremed values<br><br>Freq: %{x:.4f}  <br>"
            + "Amplitude: %{y:.2f}<br>"
            + "cluster: %{text}",
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    
    fig_main.add_trace(
        go.Scatter(
            x=freq_arr[indecies],
            y=2*amp[indecies],
            mode="markers",
            marker=dict(color=conf,colorscale=colorscale),
            text=names,
            hovertemplate="<b>Freq: %{x:.4f}    Hz<br>"
            + "Amplitude: %{y:.2f}<br>"
            + "cluster: %{text}",
            showlegend=False,
        ),
        row=2,
        col=2,
    )

    for i in range(0, len(d)):
        fig_main.add_shape(
            dict(
                type="circle",
                x0=d[i, 0] - eps,
                y0=d[i, 1] - eps,
                x1=d[i, 0] + eps,
                y1=d[i, 1] + eps,
                opacity=0.3,
            ),
            row=1,
            col=1,
            name=names[i],
            line_color=color[i],
        )

    counter = 2
    figs,names = plot_both_spectrums(args,freq_arr, amp, full = False)
    for trace in list(figs.select_traces()):
        counter += 1
        trace.update(marker={'coloraxis': f'coloraxis{counter}'})
        fig_main.append_trace(trace, row=counter, col=1)
    fig_main.update_layout(
    coloraxis3={
        "colorbar": {
            "x": 1,
            "len": .2,
            "y": 0.36,
        },
        "colorscale": colorscale
    },
    coloraxis4={
        "colorbar": {
            "x": 1,
            "len": .2,
            "y": .09,
        },
        "colorscale": colorscale
    })

    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=2, range=[-.01,1.01])
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=2, row=2)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=1, range=[-.01,1.01])
    fig_main.update_yaxes(title_text=f"Normed {name}", col=1, row=2)
    fig_main.update_yaxes(title_text=f"{name}"       , col=2, row=2)
    fig_main.update_yaxes(title_text=f"Normed {name}", col=1, row=1)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=4)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=3)
    fig_main.update_yaxes(title_text=names[0], col=1, row=3)
    fig_main.update_yaxes(title_text=names[1], col=1, row=4)
    fig_main.update_layout(
        width=1300, 
        height=1700, 
        font={"family": "Courier New, monospace", "size": 24, "color": "black"},
        template="plotly",
        )
    format_plot(fig_main)
    fig_main.show()


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