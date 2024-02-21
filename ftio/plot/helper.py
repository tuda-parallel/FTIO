import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def legend_fix(data, c) -> bool:
    if c == data.nRun - 1:
        return True
    else:
        return False


def format_plot(fig) -> go.Figure:
    """Formats plots

    Args:
        fig (plotly figure): figure from plotly
    """
    fig.update_layout(
        plot_bgcolor="white",
        legend=dict(
            bgcolor="rgba(255,255,255,.99)",
            bordercolor="Black",
            borderwidth=1,
        ),
        font=dict(family="Courier New, monospace", size=17, color="black"),
        margin=dict(r=5),
    )

    fig.update_xaxes(
        ticks="outside",
        ticklen=10,
        showgrid=True,
        mirror=True,
        showline=True,
        linecolor="black",
        gridcolor="lightgrey",
        minor_ticks="outside",
        minor=dict(
            ticklen=2, tickcolor="black", tickmode="auto", nticks=5, showgrid=True
        ),
    )

    fig.update_yaxes(
        ticks="outside",
        ticklen=10,
        showgrid=True,
        mirror=True,
        showline=True,
        linecolor="black",
        gridcolor="lightgrey",
        minor_ticks="outside",
        minor=dict(
            ticklen=2, tickcolor="black", tickmode="auto", nticks=5, showgrid=True
        ),
    )

    return fig


def save_fig(fig, f, path, name):
    length = len(f)
    index = f.index(fig)
    try:
        print(f"   -> Working on {index}/{length-1}")
        fig.write_image(f"{path}/{name}_{index}.pdf")
    except Exception as error:
        print(f"An exception occurred: {error}")
        fig.write_image(f"{index}.pdf")
    print(f"   -> Finished {index}/{length-1}")


def add_fig_row(nRun, onefig=False, specs=None, subplot_titles=None) -> go.Figure:
    if nRun == 1 or onefig == True:
        # self.f_t.append(go.Figure())
        f = make_subplots(rows=1, cols=1, specs=specs)
    else:
        f = make_subplots(rows=nRun, cols=1, specs=specs, subplot_titles=subplot_titles)

    return f


def add_fig_col(
    nRun, onefig=False, specs=None, subplot_titles=None, horizontal_spacing=0.01
) -> go.Figure:
    if nRun == 1 or onefig == True:
        # self.f_t.append(go.Figure())
        f = make_subplots(rows=1, cols=1, specs=specs)
    else:
        subplot_titles = np.arange(0, nRun).astype(str).tolist()
        subplot_titles = ["Run " + x for x in subplot_titles]
        f = make_subplots(
            rows=1,
            cols=nRun,
            specs=specs,
            shared_yaxes=True,
            subplot_titles=subplot_titles,
            horizontal_spacing=horizontal_spacing,
        )

    return f
