import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def legend_fix(data, c) -> bool:
    if c == data.nRun - 1:
        return True
    else:
        return False


def format_plot(fig: go.Figure, legend=True, font=True, x_minor=True, y_minor=True) -> go.Figure:
    """Formats plots

    Args:
        fig (go.Figure): figure from plotly
        legend (bool, optional): flag to format legend as well. Defaults to True.
        font (bool, optional): flag to format font as well. Defaults to True.

    Returns:
        go.Figure: Formatted figure
    """
    if legend:
        fig.update_layout(legend=dict(
                bgcolor="rgba(255,255,255,.99)",
                bordercolor="Black",
                borderwidth=1,
            ))
    if font:
        fig.update_layout(font=dict(
            family="Courier New, monospace", size=17, color="black"
            ))

    fig.update_layout(
        plot_bgcolor="white",
        margin=dict(r=5),
    )

    x_settings = dict(
        ticks = "outside",
        ticklen = 10,
        mirror = True,
        showgrid = True,
        showline = True,
        linecolor = "black",
        gridcolor = "lightgrey"
        )
    if x_minor:
        x_settings['minor_ticks'] = "outside"
        x_settings['minor'] = dict(
            ticklen=2, tickcolor="black", tickmode="auto", nticks=5, showgrid=True
        )

    fig.update_xaxes(**x_settings)
    
    y_settings = dict(
        ticks = "outside",
        ticklen = 10,
        mirror = True,
        showgrid = True,
        showline = True,
        linecolor = "black",
        gridcolor = "lightgrey"
        )
    if y_minor:
        y_settings['minor_ticks'] = "outside"
        y_settings['minor'] = dict(
            ticklen=2, tickcolor="black", tickmode="auto", nticks=5, showgrid=True
        )

    fig.update_yaxes(**y_settings)

    return fig


def format_plot_simple(fig) -> go.Figure:
    """makes plots uniform

    Args:
        fig (pltoly figure)
    """
    fig.update_layout(
        plot_bgcolor="white",
        legend=dict(
            bgcolor="rgba(255,255,255,.99)",
            bordercolor="Black",
            borderwidth=1,
        ),
        font=dict(family="Courier New, monospace", size=24, color="black"),
        # margin=dict(l=5, r=5, t=5, b=5) #IEEE
        margin=dict(t=25),
    )

    fig.update_xaxes(
        ticks="outside",
        # tickwidth=1,
        ticklen=10,
        showgrid=True,
        # gridwidth=1,
        mirror=True,
        showline=True,
        linecolor="black",
        gridcolor="lightgrey",
        minor_ticks="outside",
        minor=dict(ticklen=2),
    )

    fig.update_yaxes(
        ticks="outside",
        # tickwidth=1,
        ticklen=10,
        showgrid=True,
        # gridwidth=1,
        mirror=True,
        showline=True,
        linecolor="black",
        gridcolor="lightgrey",
        minor_ticks="outside",
        minor=dict(ticklen=2),
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
