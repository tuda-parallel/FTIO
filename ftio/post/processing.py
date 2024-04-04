import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from ftio.freq.helper import format_plot


def label_phases(
    prediction: dict, args, b0: np.ndarray = np.array([]), t0: np.ndarray = np.array([])
):
    """Labels the phases using the result from FTIO

    Args:
        prediction (dict): prediction from FTIO
        args (Argparse): arguments passed to FTIO
        b0 (np.ndarray, optional): original bandwidth. Defaults to np.array([]).
        t0 (np.ndarray, optional): original time. Defaults to np.array([]).

    Returns:
        _type_: _description_
    """
    # just take the dominant or consider more than one
    only0ne = False
    t = np.arange(
            prediction["t_start"], prediction["t_end"], 1 / prediction["freq"]
        )

    if only0ne:
        dominant_index = np.argmax(prediction["conf"])
        # conf = prediction["conf"][dominant_index]
        f = prediction["dominant_freq"][dominant_index]
        amp = prediction["amp"][dominant_index]
        phi = prediction["phi"][dominant_index]
        n = np.floor((prediction["t_end"] - prediction["t_start"]) * prediction["freq"])

        ## create cosine wave
        cosine_wave = 2 * amp / n * np.cos(2 * np.pi * f * t + phi)
    else:
        cosine_wave = np.zeros(len(t))
        print(f"merging {len(prediction['conf'])} frequencies")

        for index in range(0, len(prediction["conf"])):
            # conf = prediction["conf"][index]
            f = prediction["dominant_freq"][index]
            amp = prediction["amp"][index]
            phi = prediction["phi"][index]
            n = np.floor(
                (prediction["t_end"] - prediction["t_start"]) * prediction["freq"]
            )

            ## create cosine wave
            cosine_wave = cosine_wave + 2 * amp / n * np.cos(2 * np.pi * f * t + phi)

    ## make square signal
    square_wave = np.zeros(len(cosine_wave))
    top = np.max(cosine_wave)
    for i, x in enumerate(cosine_wave):
        if x > 0:
            square_wave[i] = top
        else:
            square_wave[i] = -top

    phases = []
    tmp = []
    for i, x in enumerate(square_wave):
        if i == 0:
            counter = 0
            mem = x
            phases.append(counter)
            tmp.append(t[i])
        else:
            if mem == x:
                pass
            else:
                mem = x
                counter += 1
                phases.append(counter)
                tmp.append(t[i])

    # Assign in not empty
    if tmp:
        # add end time
        tmp.append(t[-1])
        time = {"t_s": tmp[0:-1], "t_e": tmp[1:]}
    else:
        time = {"t_s": [], "t_e": []}

    ## Plot
    fig = plot_classification(args, cosine_wave, t, time, b0,t0)

    return phases, time


def plot_classification(args, cosine_wave, t, time, b0,t0)  -> go.Figure | None:
    fig = None
    if any(x in args.engine for x in ["mat", "plot"]):
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=t, y=cosine_wave, name="FTIO cosine wave", marker_color="red")
        )
        # fig.add_trace(go.Scatter(x=t, y=square_wave, name="square wave"))
        fig.add_hline(y=0, line_width=1, line_color="gray")
        colors = px.colors.qualitative.Plotly + px.colors.qualitative.G10
        for i, _ in enumerate(time["t_s"]):
            fig.add_vrect(
                x0=time["t_s"][i],
                x1=time["t_e"][i],
                annotation_text=f"phase {i}",
                annotation_position="top",
                fillcolor=colors[i],
                opacity=0.25,
                line_width=0,
            )

        if b0.size > 0:
            fig.add_trace(
                go.Scatter(
                    x=t0,
                    y=b0,
                    mode="lines+markers",
                    name="Original signal",
                    marker_color="rgb(0,150,250)",
                )
            )

        fig.update_layout(
            xaxis_title="Ranks",
            yaxis_title="Transfer Rate (B/s)",
            width=1800,
            height=600,
        )
        fig = format_plot(fig)
        fig.show()

        return fig