from argparse import Namespace
import numpy as np
import plotly.graph_objects as go
from ftio.plot.helper import format_plot

def plot_autocorr_results(args: Namespace, acorr: np.ndarray, peaks: np.ndarray, outliers: np.ndarray,
                          flag: bool = False):
    """
    Plots the autocorrelation results using Plotly.

    Args:
        args (Namespace): Command line arguments.
        acorr (np.ndarray): Autocorrelation values.
        peaks (np.ndarray): Indices of the peaks in the autocorrelation.
        outliers (np.ndarray): Indices of the outliers in the peaks.
        flag (bool, optional): Flag to indicate whether to plot relevant peaks. Defaults to False.

    Retrurns:
        Figure: Plotly or matplotlib figure.
    """
    fig = None
    if any(x in args.engine for x in ["mat", "plot"]):
        fig = go.Figure()
        fig.add_scatter(
            y=acorr,
            mode="markers+lines",
            name="ACF",
            marker=dict(
                color=acorr,
                colorscale=["rgb(0,50,150)", "rgb(150,50,150)", "rgb(255,50,0)"],
                showscale=True,
            ),
        )
        fig.update_layout(
            font={"family": "Courier New, monospace", "size": 24, "color": "black"},
            xaxis_title="Lag (Samples)",
            yaxis_title="ACF",
            width=1100,
            height=400,  # 500
        )
        fig.update_layout(
            coloraxis_colorbar=dict(
                yanchor="top", y=1, x=0, ticks="outside", ticksuffix=" bills"
            )
        )
        # fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.01))
        fig.update_layout(
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
        )
        fig = format_plot(fig)

        # plot peaks
        fig.add_scatter(
            x=peaks,
            y=acorr[peaks],
            marker=dict(
                color="rgba(20, 220, 70, 0.9)",
                size=14,  # 12,
                symbol="star-triangle-up",
                angle=0,
                line=dict(width=1, color="DarkSlateGrey"),
            ),
            mode="markers",
            name="peaks",
        )

        # plot candidates
        if flag:
            val = np.delete(peaks, outliers)
            fig.add_scatter(
                x=val,
                y=acorr[val],
                marker=dict(
                    color="rgba(220, 20, 70, 0.9)",
                    size=21,  # 19,
                    symbol="circle-open-dot",
                    angle=0,
                    line=dict(width=2, color="DarkSlateGrey"),
                ),
                mode="markers",
                name="relevant peaks",
            )

        fig = format_plot(fig)

    return fig