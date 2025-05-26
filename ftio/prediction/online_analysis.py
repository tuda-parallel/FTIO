"""Performs the analysis for prediction. This includes the calculation of ftio and parsing of the data into a queue"""

from __future__ import annotations

from argparse import Namespace

import numpy as np
from rich.console import Console

from ftio.cli import ftio_core
from ftio.freq.prediction import Prediction
from ftio.plot.plot_bandwidth import plot_bar_with_rich
from ftio.plot.units import set_unit
from ftio.prediction.helper import get_dominant
from ftio.prediction.shared_resources import SharedResources


def ftio_process(
    shared_resources: SharedResources, args: list[str], msgs=None
) -> None:
    """Perform a single prediction

    Args:
        shared_resources (SharedResources): shared resources among processes
        args (list[str]): additional arguments passed to ftio
    """
    console = Console()
    console.print(
        f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/]  Started"
    )

    # Modify the arguments
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{shared_resources.start_time.value:.2f}"])
    # perform prediction
    prediction, parsed_args = ftio_core.main(args, msgs)
    if not prediction:
        console.print("[yellow]Terminating prediction (no data passed) [/]")
        console.print(
            f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/]  Stopped"
        )
        exit(0)

    if not isinstance(prediction, list) or len(prediction) != 1:
        raise ValueError(
            "[red][PREDICTOR] (#{shared_resources.count.value}):[/]  predictor should be called on exactly on file"
        )

    # get the prediction
    prediction = prediction[-1]
    # plot_bar_with_rich(shared_resources.t_app,shared_resources.b_app, width_percentage=0.9)

    # get data
    freq = get_dominant(prediction)  # just get a single dominant value

    # save prediction results
    save_data(prediction, shared_resources)

    # display results
    text = display_result(freq, prediction, shared_resources)

    # data analysis to decrease window thus change start_time
    text += window_adaptation(parsed_args, prediction, freq, shared_resources)

    # print text
    console.print(text)


def window_adaptation(
    args: Namespace,
    prediction: Prediction,
    freq: float,
    shared_resources: SharedResources,
) -> str:
    """modifies the start time if conditions are true

    Args:
        args (argparse): command line arguments
        prediction (Prediction): result from FTIO
        freq (float|Nan): dominant frequency
        shared_resources (SharedResources): shared resources among processes
        text (str): text to display

    Returns:
        str: _description_
    """
    # average data/data processing
    text = ""
    t_s = prediction.t_start
    t_e = prediction.t_end
    total_bytes = prediction.total_bytes

    # Hits
    text += hits(args, prediction, shared_resources)

    # time window adaptation
    if not np.isnan(freq):
        n_phases = (t_e - t_s) * freq
        avr_bytes = int(total_bytes / float(n_phases))
        unit, order = set_unit(avr_bytes, "B")
        avr_bytes = order * avr_bytes

        # FIXME this needs to compensate for a smaller windows
        if not args.window_adaptation:
            text += (
                f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Estimated phases {n_phases:.2f}\n"
                f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Average transferred {avr_bytes:.0f} {unit}\n"
            )

        # adaptive time window
        if "frequency_hits" in args.window_adaptation:
            if shared_resources.hits.value > args.hits:
                if (
                    True
                ):  # np.abs(avr_bytes - (total_bytes-aggregated_bytes.value)) < 100:
                    tmp = t_e - 3 * 1 / freq
                    t_s = tmp if tmp > 0 else 0
                    text += f"[bold purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] Adjusting start time to {t_s} sec\n[/]"
            else:
                t_s = 0
                if shared_resources.hits.value == 0:
                    text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/][red bold] Resetting start time to {t_s} sec\n[/]"
        elif (
            "data" in args.window_adaptation and len(shared_resources.data) > 0
        ):
            text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] Trying time window adaptation: {shared_resources.count.value:.0f} =? { args.hits * shared_resources.hits.value:.0f}\n[/]"
            if (
                shared_resources.count.value
                == args.hits * shared_resources.hits.value
            ):
                # t_s = shared_resources.data[-shared_resources.count.value]['t_start']
                # text += f'[bold purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] Adjusting start time to t_start {t_s} sec\n[/]'
                if len(shared_resources.t_flush) > 0:
                    print(shared_resources.t_flush)
                    index = int(args.hits * shared_resources.hits.value - 1)
                    t_s = shared_resources.t_flush[index]
                    text += f"[bold purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] Adjusting start time to t_flush[{index}] {t_s} sec\n[/]"

    # TODO 1: Make sanity check -- see if the same number of bytes was transferred
    # TODO 2: Train a model to validate the predictions?
    text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Ended"
    shared_resources.start_time.value = t_s
    return text


def save_data(prediction, shared_resources) -> None:
    """Put all data from `prediction` in a `queue`. The total bytes are as well saved here.

    Args:
        prediction (dict): result from FTIO
        shared_resources (SharedResources): shared resources among processes
    """
    # safe total transferred bytes
    shared_resources.aggregated_bytes.value += prediction.total_bytes

    # save data
    shared_resources.queue.put(
        {
            "phase": shared_resources.count.value,
            "dominant_freq": prediction.dominant_freq,
            "conf": prediction.conf,
            "amp": prediction.amp,
            "phi": prediction.phi,
            "t_start": prediction.t_start,
            "t_end": prediction.t_end,
            "total_bytes": prediction.total_bytes,
            "ranks": prediction.ranks,
            "freq": prediction.freq,
            # 'hits': shared_resources.hits.value,
        }
    )


def display_result(
    freq: float, prediction: Prediction, shared_resources: SharedResources
) -> str:
    """Displays the results from FTIO

    Args:
        freq (float): dominant frequency
        prediction (Prediction): prediction setting from FTIO
        shared_resources (SharedResources): shared resources among processes

    Returns:
        str: text to print to console
    """
    text = ""
    # Dominant frequency
    if not np.isnan(freq):
        text = f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Dominant freq {freq:.3f} Hz ({1/freq if freq != 0 else 0:.2f} sec)\n"

    # Candidates
    text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Freq candidates: \n"
    for i, f_d in enumerate(prediction.dominant_freq):
        text += (
            f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/]    {i}) "
            f"{f_d:.2f} Hz -- conf {prediction.conf[i]:.2f}\n"
        )

    # time window
    text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Time window {prediction.t_end-prediction.t_start:.3f} sec ([{prediction.t_start:.3f},{prediction.t_end:.3f}] sec)\n"

    # total bytes
    total_bytes = shared_resources.aggregated_bytes.value
    # total_bytes =  prediction.total_bytes
    unit, order = set_unit(total_bytes, "B")
    total_bytes = order * total_bytes
    text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Total bytes {total_bytes:.0f} {unit}\n"

    # Bytes since last time
    # tmp = abs(prediction.total_bytes -shared_resources.aggregated_bytes.value)
    tmp = abs(shared_resources.aggregated_bytes.value)
    unit, order = set_unit(tmp, "B")
    tmp = order * tmp
    text += (
        f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Bytes transferred since last "
        f"time {tmp:.0f} {unit}\n"
    )

    return text


def hits(args, prediction, shared_resources):
    text = ""
    if "frequency_hits" in args.window_adaptation:
        if len(prediction.dominant_freq) == 1:
            shared_resources.hits.value += 1
            text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Current hits {shared_resources.hits.value}\n"
        else:
            shared_resources.hits.value = 0
            text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/][red bold] Resetting hits {shared_resources.hits.value}[/]\n"
    elif "data" in args.window_adaptation:
        shared_resources.hits.value = shared_resources.count.value // args.hits
        text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Current hits {shared_resources.hits.value}\n"

    return text
