"""Performs the analysis for prediction. This includes the calculation of ftio and parsing of the data into a queue

Author: Ahmad Tarraf
Copyright (c) 2026 TU Darmstadt, Germany
Version: v0.0.7
Date: Mai 2025
Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE"""

from __future__ import annotations

import time
from argparse import Namespace

import numpy as np
from rich.console import Console

from ftio.cli import ftio_core
from ftio.freq.prediction import Prediction
from ftio.gui.socket_logger import get_socket_logger, log_to_gui_and_console
from ftio.plot.units import set_unit
from ftio.prediction.change_detection.adwin import (
    AdwinDetector,
    detect_pattern_change_adwin,
)
from ftio.prediction.change_detection.cusum import (
    CUSUMDetector,
    detect_pattern_change_cusum,
)
from ftio.prediction.change_detection.helper import (
    change_post_processing,
    create_change_point_info,
)
from ftio.prediction.change_detection.pagehinkley import (
    SelfTuningPageHinkleyDetector,
    detect_pattern_change_pagehinkley,
)
from ftio.prediction.helper import get_dominant
from ftio.prediction.shared_resources import SharedResources


def ftio_process(shared_resources: SharedResources, args: Namespace, msgs=None) -> None:
    """Perform a single prediction with FTIO

    Args:
        shared_resources (SharedResources): shared resources among processes
        args (Namespace): arguments passed to ftio
        msgs: ZMQ messages (optional)
    """
    console = Console()
    pred_id = shared_resources.count.value
    start_msg = f"[purple][PREDICTOR] (#{pred_id}):[/] Started"
    gui_enabled = "gui" in args
    log_to_gui_and_console(
        gui_enabled, console, start_msg, "predictor_start", {"count": pred_id}
    )

    # Modify the arguments
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{shared_resources.start_time.value:.2f}"])
    # perform prediction
    prediction_list, parsed_args = ftio_core.main(args, msgs, shared_resources)
    if not prediction_list:
        log_to_gui_and_console(
            gui_enabled,
            console,
            "[yellow]Terminating prediction (no data passed)[/]",
            "termination",
            {"reason": "no_data"},
        )
        return

    # get latest prediction
    prediction = prediction_list[-1]
    # plot_bar_with_rich(shared_resources.t_app,shared_resources.b_app, width_percentage=0.9)

    # get dominant frequency
    freq = get_dominant(prediction)

    # save prediction results
    save_data(prediction, shared_resources)

    # display results
    text = display_result(freq, prediction, shared_resources)

    # data analysis to decrease window by changing start_time
    adaptation_text, change_detected, change_point_info = window_adaptation(
        parsed_args, prediction, freq, shared_resources
    )
    text += adaptation_text
    candidates = [
        {"frequency": f, "confidence": c}
        for f, c in zip(prediction.dominant_freq, prediction.conf, strict=True)
    ]
    if candidates:
        best = max(candidates, key=lambda c: c["confidence"])
        dominant_freq = best["frequency"]
        dominant_period = 1.0 / dominant_freq if dominant_freq > 0 else 0.0
        confidence = best["confidence"]
    else:
        dominant_freq = dominant_period = confidence = 0.0

    if gui_enabled:
        logger = get_socket_logger()
        if logger is not None:
            structured_prediction = {
                "prediction_id": pred_id,
                "timestamp": str(time.time()),
                "dominant_freq": dominant_freq,
                "dominant_period": dominant_period,
                "confidence": confidence,
                "candidates": candidates,
                "time_window": (float(prediction.t_start), float(prediction.t_end)),
                "total_bytes": str(prediction.total_bytes),
                "bytes_transferred": str(prediction.total_bytes),
                "current_hits": int(shared_resources.hits.value),
                "periodic_probability": 0.0,
                "frequency_range": (0.0, 0.0),
                "period_range": (0.0, 0.0),
                "change_detected": change_detected,
                "change_point": change_point_info,
            }
            logger.send_log(
                "prediction", "FTIO structured prediction", structured_prediction
            )

    # print text
    log_to_gui_and_console(
        gui_enabled,
        console,
        text,
        "prediction_log",
        {"count": pred_id, "freq": dominant_freq},
    )
    # shared_resources.count.value += 1


def window_adaptation(
    args: Namespace,
    prediction: Prediction,
    freq: float,
    shared_resources: SharedResources,
) -> tuple[str, bool, dict]:
    """Modifies the start time if conditions are true. Also performs change point detection.

    Args:
        args (argparse): command line arguments
        prediction (Prediction): result from FTIO
        freq (float|NaN): dominant frequency
        shared_resources (SharedResources): shared resources among processes

    Returns:
        tuple: (text, change_detected, change_point_info)
    """
    # Initialize output and prediction info
    text = ""
    t_s, t_e = prediction.t_start, prediction.t_end
    total_bytes = prediction.total_bytes
    prediction_count = shared_resources.count.value

    # Hits
    text += hits(args, prediction, shared_resources)

    # ---------------------- Intermediate info ----------------------
    if not np.isnan(freq) and freq > 0:
        time_window = t_e - t_s
        n_phases = avr_bytes = 0
        unit = "B"

        if time_window > 0:
            n_phases = time_window * freq
            if n_phases > 0:
                avr_bytes = int(total_bytes / n_phases)
                unit_factor, order = set_unit(avr_bytes, "B")
                avr_bytes = avr_bytes * order

        # FIXME: this needs to compensate for smaller windows
        if not args.window_adaptation:
            text += (
                f"[purple][PREDICTOR] (#{prediction_count}):[/] "
                f"Estimated phases {n_phases:.2f}\n"
                f"[purple][PREDICTOR] (#{prediction_count}):[/] "
                f"Average transferred {avr_bytes:.0f} {unit}\n"
            )

    # ---------------------- Change point detection ----------------------
    change_detected = False
    change_point_info = None
    if prediction_count == 0:
        shared_resources.online_detection["change_count"] = 0
        shared_resources.online_detection["last_change_time"] = t_s
        shared_resources.online_detection["state"] = {}

    if args.window_adaptation is not None:
        # Select and run the appropriate detector
        if args.window_adaptation in {"cusum", "ph", "adwin"}:
            # create a local copy so that it is not affected by other procs
            past_predictions = list(shared_resources.data)
            online_detection = dict(shared_resources.online_detection)
            if args.window_adaptation == "cusum":
                detector = CUSUMDetector(
                    window_size=50,
                    past_predictions=past_predictions,
                    online_detection=online_detection,
                    verbose=args.verbose,
                )
                change_detected, log, detected_t_s, old_freq, new_freq = (
                    detect_pattern_change_cusum(
                        args, shared_resources, prediction, detector, prediction_count
                    )
                )
            elif args.window_adaptation == "ph":
                detector = SelfTuningPageHinkleyDetector(
                    past_predictions=past_predictions,
                    online_detection=online_detection,
                    verbose=args.verbose,
                )
                change_detected, log, detected_t_s, old_freq, new_freq = (
                    detect_pattern_change_pagehinkley(
                        args, shared_resources, prediction, detector, prediction_count
                    )
                )
            elif args.window_adaptation == "adwin":
                detector = AdwinDetector(
                    delta=0.05,
                    past_predictions=past_predictions,
                    online_detection=online_detection,
                    verbose=args.verbose,
                )
                change_detected, log, detected_t_s, old_freq, new_freq = (
                    detect_pattern_change_adwin(
                        args, shared_resources, prediction, detector, prediction_count
                    )
                )
            else:
                raise ValueError(
                    f"Unknown online adaptation algorithm: {args.window_adaptation}"
                )
            frequency_count = len(shared_resources.data)
            text += f"{log}\n" if log else ""
            # create info for logger
            change_point_info = create_change_point_info(
                prediction_count,
                t_e,
                old_freq,
                new_freq,
                detected_t_s,
                frequency_count,
            )
            t_s, text = change_post_processing(
                args, prediction_count, t_e, t_s, detected_t_s, text
            )

        # Frequency hits adaptation
        elif "frequency_hits" in args.window_adaptation:
            if shared_resources.hits.value > args.hits:
                tmp = max(t_e - 3 / freq, 0)
                t_s = tmp
                text += f"[bold purple][PREDICTOR] (#{prediction_count}):[/][green] Adjusting start time to {t_s} sec\n[/]"
                shared_resources.online_detection["change_count"] += 1
                shared_resources.online_detection["last_change_time"] = t_s
            else:
                t_s = 0
                if shared_resources.hits.value == 0:
                    text += f"[purple][PREDICTOR] (#{prediction_count}):[/][red bold] Resetting start time to {t_s} sec\n[/]"

        # Data-based adaptation
        elif "data" in args.window_adaptation:
            if len(shared_resources.data) > 0:
                test = (
                    np.floor(prediction_count / args.hits) if prediction_count != 0 else 0
                )
                text += f"[purple][PREDICTOR] (#{prediction_count}):[/][green] Trying time window adaptation: {test:.0f} =? {shared_resources.hits.value:.0f}\n[/]"
                if (
                    test == shared_resources.hits.value
                    and shared_resources.hits.value > 0
                ):
                    # t_s = shared_resources.data[-shared_resources.count.value]['t_start']
                    # text += f'[bold purple][PREDICTOR] (#{prediction_count}):[/][green] Adjusting start time to t_start {t_s} sec\n[/]'
                    index = int(prediction_count - 1)
                    shared_resources.hits.value = 0
                    if len(shared_resources.t_flush) > 0:
                        t_s = shared_resources.t_flush[index]
                        text += f"[bold purple][PREDICTOR] (#{prediction_count}):[/][green] Adjusting start time to t_flush[{index}] {t_s} sec\n[/]"
                    else:
                        t_s = shared_resources.data[index]["t_end"]
                        text += f"[bold purple][PREDICTOR] (#{prediction_count}):[/][green] Adjusting start time to t_end[{index}] {t_s} sec\n[/]"

                    shared_resources.online_detection["change_count"] += 1
                    shared_resources.online_detection["last_change_time"] = t_s

        else:
            raise ValueError(
                f"Unknown online adaptation algorithm: {args.window_adaptation}"
            )

        # ---------------------- Summary ----------------------
        if not np.isnan(freq):
            frequencies = [get_dominant(d) for d in list(shared_resources.data)]
            frequencies.append(freq)
            samples = len(frequencies)
            changes = shared_resources.online_detection["change_count"]
            recent_freqs = (
                list(frequencies)[-5:] if len(frequencies) >= 5 else list(frequencies)
            )
            success_rate = (
                samples / (prediction_count + 1) * 100 if prediction_count + 1 > 0 else 0
            )

            text += (
                f"\n[purple][PREDICTOR] (#{prediction_count}): [bold cyan]{'=' * 50}[/]\n"
            )
            text += f"[purple][PREDICTOR] (#{prediction_count}): [bold cyan]{args.window_adaptation.upper()} ANALYSIS (Prediction #{prediction_count})[/]\n"
            text += f"[purple][PREDICTOR] (#{prediction_count}): [cyan]Frequency detections: {samples}/{prediction_count + 1} ({success_rate:.1f}% coverage)[/]\n"
            text += f"[purple][PREDICTOR] (#{prediction_count}): [cyan]Pattern changes detected: {changes}[/]\n"
            text += f"[purple][PREDICTOR] (#{prediction_count}): [cyan]Current frequency: {freq:.3f} Hz ({1 / freq:.2f}s period)[/]\n"
            text += f"[purple][PREDICTOR] (#{prediction_count}): [cyan]Time window: [{t_s:.2f} -- {t_e:.2f}] s[/]\n"

            if samples > 1 and args.verbose:
                text += f"[cyan][purple][PREDICTOR] (#{prediction_count}): Recent freq history: {[f'{f:.3f}Hz' for f in recent_freqs]}[/]\n"
                if len(recent_freqs) >= 2:
                    trend = (
                        "increasing"
                        if recent_freqs[-1] > recent_freqs[-2]
                        else (
                            "decreasing"
                            if recent_freqs[-1] < recent_freqs[-2]
                            else "stable"
                        )
                    )
                    text += f"[purple][PREDICTOR] (#{prediction_count}): [cyan]Frequency trend: {trend}[/]\n"

            text += f"[cyan][purple][PREDICTOR] (#{prediction_count}): {args.window_adaptation.upper()} window size: {samples} samples[/]\n"
            text += f"[purple][PREDICTOR] (#{prediction_count}): [cyan]{args.window_adaptation.upper()} changes detected: {changes}[/]\n"
            text += (
                f"[purple][PREDICTOR] (#{prediction_count}): [bold cyan]{'=' * 50}[/]\n\n"
            )

    # TODO 1: Make sanity check -- see if the same number of bytes was transferred
    # TODO 2: Train a model to validate the predictions?

    text += f"[purple][PREDICTOR] (#{prediction_count}):[/] Ended"

    # set change time
    shared_resources.start_time.value = t_s
    return text, change_detected, change_point_info


def save_data(prediction: Prediction, shared_resources) -> None:
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
    # Dominant frequency
    if not np.isnan(freq):
        text = f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Dominant freq {freq:.3f} Hz ({1 / freq if freq != 0 else 0:.2f} sec)\n"
    else:
        text = f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] No dominant frequency found\n"

    # Candidates
    if len(prediction.dominant_freq) > 0:
        text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Freq candidates ({len(prediction.dominant_freq)} found): \n"
        for i, f_d in enumerate(prediction.dominant_freq):
            text += (
                f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/]    {i}) "
                f"{f_d:.2f} Hz -- conf {prediction.conf[i]:.2f}\n"
            )
    else:
        text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] No frequency candidates detected\n"

    # time window
    text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Time window {prediction.t_end - prediction.t_start:.3f} sec ([{prediction.t_start:.3f},{prediction.t_end:.3f}] sec)\n"

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
    if args.window_adaptation is not None:
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
