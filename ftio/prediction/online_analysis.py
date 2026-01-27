"""Performs the analysis for prediction. This includes the calculation of ftio and parsing of the data into a queue"""

from __future__ import annotations

from argparse import Namespace
import numpy as np
import socket
import json
import time
from rich.console import Console

from ftio.cli import ftio_core
from ftio.freq.prediction import Prediction
from ftio.plot.units import set_unit
from ftio.prediction.helper import get_dominant
from ftio.prediction.shared_resources import SharedResources
from ftio.prediction.change_point_detection import ChangePointDetector, detect_pattern_change_adwin, CUSUMDetector, detect_pattern_change_cusum, SelfTuningPageHinkleyDetector, detect_pattern_change_pagehinkley


class SocketLogger:
    
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Attempt to connect to the GUI server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(1.0)  # 1 second timeout
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[INFO] Connected to GUI server at {self.host}:{self.port}")
        except (socket.error, ConnectionRefusedError, socket.timeout) as e:
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            print(f"[WARNING] Failed to connect to GUI server at {self.host}:{self.port}: {e}")
            print(f"[WARNING] GUI logging disabled - messages will only appear in console")
    
    def send_log(self, log_type: str, message: str, data: dict = None):
        if not self.connected:
            return  
        
        try:
            log_data = {
                'timestamp': time.time(),
                'type': log_type,
                'message': message,
                'data': data or {}
            }
            
            json_data = json.dumps(log_data) + '\n'
            self.socket.send(json_data.encode('utf-8'))

        except (socket.error, BrokenPipeError, ConnectionResetError) as e:
            print(f"[WARNING]  Failed to send to GUI: {e}")
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False


_socket_logger = None

def get_socket_logger():
    global _socket_logger
    if _socket_logger is None:
        _socket_logger = SocketLogger()
    return _socket_logger

def strip_rich_formatting(text: str) -> str:
    import re
    
    clean_text = re.sub(r'\[/?(?:purple|blue|green|yellow|red|bold|dim|/)\]', '', text)
    
    clean_text = re.sub(r'\[(?:purple|blue|green|yellow|red|bold|dim)\[', '[', clean_text)
    
    return clean_text

def log_to_gui_and_console(console: Console, message: str, log_type: str = "info", data: dict = None):
    logger = get_socket_logger()
    clean_message = strip_rich_formatting(message)
    
    console.print(message)
    
    logger.send_log(log_type, clean_message, data)


def get_change_detector(shared_resources: SharedResources, algorithm: str = "adwin"):
    console = Console()
    algo = (algorithm or "adwin").lower()
    global _local_detector_cache
    if '_local_detector_cache' not in globals():
        _local_detector_cache = {}

    detector_key = f"{algo}_detector"

    if detector_key in _local_detector_cache:
        return _local_detector_cache[detector_key]

    show_init_message = not shared_resources.detector_initialized.value

    if algo == "cusum":
        detector = CUSUMDetector(window_size=50, shared_resources=shared_resources, show_init=show_init_message, verbose=True)
    elif algo == "ph":
        detector = SelfTuningPageHinkleyDetector(shared_resources=shared_resources, show_init=show_init_message, verbose=True)
    else:
        detector = ChangePointDetector(delta=0.05, shared_resources=shared_resources, show_init=show_init_message, verbose=True)

    _local_detector_cache[detector_key] = detector
    shared_resources.detector_initialized.value = True
    return detector

def ftio_process(shared_resources: SharedResources, args: list[str], msgs=None) -> None:
    """Perform a single prediction

    Args:
        shared_resources (SharedResources): shared resources among processes
        args (list[str]): additional arguments passed to ftio
        msgs: ZMQ messages (optional)
    """
    console = Console()
    pred_id = shared_resources.count.value
    start_msg = f"[purple][PREDICTOR] (#{pred_id}):[/] Started"
    log_to_gui_and_console(console, start_msg, "predictor_start", {"count": pred_id})

    # Modify the arguments
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{shared_resources.start_time.value:.2f}"])
    # perform prediction
    prediction_list, parsed_args = ftio_core.main(args, msgs)
    if not prediction_list:
        log_to_gui_and_console(console,
            "[yellow]Terminating prediction (no data passed)[/]",
            "termination", {"reason": "no_data"})
        return

    # get the prediction
    prediction = prediction_list[-1]
    # plot_bar_with_rich(shared_resources.t_app,shared_resources.b_app, width_percentage=0.9)

    # get data
    freq = get_dominant(prediction) or 0.0  # just get a single dominant value

    # save prediction results
    save_data(prediction, shared_resources)

    # display results
    text = display_result(freq, prediction, shared_resources)
    # data analysis to decrease window thus change start_time
    # Get change point info directly from window_adaptation
    adaptation_text, is_change_point, change_point_info = window_adaptation(
        parsed_args, prediction, freq, shared_resources
    )
    text += adaptation_text
    candidates = [
        {"frequency": f, "confidence": c}
        for f, c in zip(prediction.dominant_freq, prediction.conf)
    ]
    if candidates:
        best = max(candidates, key=lambda c: c["confidence"])
        dominant_freq = best["frequency"]
        dominant_period = 1.0 / dominant_freq if dominant_freq > 0 else 0.0
        confidence = best["confidence"]
    else:
        dominant_freq = dominant_period = confidence = 0.0

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
        "is_change_point": is_change_point,
        "change_point": change_point_info,
    }

    get_socket_logger().send_log("prediction", "FTIO structured prediction", structured_prediction)
    # print text
    log_to_gui_and_console(console, text, "prediction_log", {"count": pred_id, "freq": dominant_freq})

    shared_resources.count.value += 1



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
        freq (float|Nan): dominant frequency
        shared_resources (SharedResources): shared resources among processes

    Returns:
        tuple: (text, is_change_point, change_point_info)
    """
    # average data/data processing
    text = ""
    t_s = prediction.t_start
    t_e = prediction.t_end
    total_bytes = prediction.total_bytes

    prediction_count = shared_resources.count.value
    text += f"Prediction #{prediction_count}\n"

    # Hits
    text += hits(args, prediction, shared_resources)

    algorithm = args.online_adaptation

    # Change point detection - capture data directly
    detector = get_change_detector(shared_resources, algorithm)
    old_freq = freq  # Store current freq before detection
    if algorithm == "cusum":
        change_detected, change_log, adaptive_start_time = detect_pattern_change_cusum(
            shared_resources, prediction, detector, shared_resources.count.value
        )
    elif algorithm == "ph":
        change_detected, change_log, adaptive_start_time = detect_pattern_change_pagehinkley(
            shared_resources, prediction, detector, shared_resources.count.value
        )
    else:
        change_detected, change_log, adaptive_start_time = detect_pattern_change_adwin(
            shared_resources, prediction, detector, shared_resources.count.value
        )

    # Build change point info directly - no regex needed
    change_point_info = None
    if change_detected:
        old_freq_val = float(old_freq) if not np.isnan(old_freq) else 0.0
        new_freq_val = float(freq) if not np.isnan(freq) else 0.0
        freq_change_pct = abs(new_freq_val - old_freq_val) / old_freq_val * 100 if old_freq_val > 0 else 0.0
        sample_count = len(shared_resources.detector_frequencies)
        change_point_info = {
            "prediction_id": shared_resources.count.value,
            "timestamp": float(prediction.t_end),
            "old_frequency": old_freq_val,
            "new_frequency": new_freq_val,
            "frequency_change_percent": freq_change_pct,
            "sample_number": sample_count,
            "cut_position": sample_count - 1 if sample_count > 0 else 0,
            "total_samples": sample_count,
            "start_time": float(adaptive_start_time)
        }

    if np.isnan(freq):
        detector_samples = len(shared_resources.detector_frequencies)
        detector_changes = shared_resources.detector_change_count.value
        text += f"[dim][{algorithm.upper()} STATE: {detector_samples} samples, {detector_changes} changes detected so far][/]\n"
        if detector_samples > 0:
            last_freq = shared_resources.detector_frequencies[-1] if shared_resources.detector_frequencies else "None"
            text += f"[dim][LAST KNOWN FREQ: {last_freq:.3f} Hz][/]\n"
    
    if change_detected and change_log:
        text += f"{change_log}\n"
        min_window_size = 1.0
        safe_adaptive_start = min(adaptive_start_time, t_e - min_window_size)

        if safe_adaptive_start >= 0 and (t_e - safe_adaptive_start) >= min_window_size:
            t_s = safe_adaptive_start
            algorithm_name = args.online_adaptation.upper() if hasattr(args, 'online_adaptation') else "UNKNOWN"
            text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] {algorithm_name} adapted window to start at {t_s:.3f}s (window size: {t_e - t_s:.3f}s)[/]\n"
        else:
            t_s = max(0, t_e - min_window_size)
            algorithm_name = args.online_adaptation.upper() if hasattr(args, 'online_adaptation') else "UNKNOWN"
            text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/][yellow] {algorithm_name} adaptation would create unsafe window, using conservative {min_window_size}s window[/]\n"

    # time window adaptation
    if not np.isnan(freq) and freq > 0:
        time_window = t_e - t_s
        if time_window > 0:
            n_phases = time_window * freq
            if n_phases > 0:
                avr_bytes = int(total_bytes / float(n_phases))
                unit, order = set_unit(avr_bytes, "B")
                avr_bytes = order * avr_bytes
            else:
                n_phases = 0
                avr_bytes = 0
                unit = "B"
        else:
            n_phases = 0
            avr_bytes = 0
            unit = "B"

        # FIXME this needs to compensate for a smaller windows
        if not args.window_adaptation:
            text += (
                f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Estimated phases {n_phases:.2f}\n"
                f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Average transferred {avr_bytes:.0f} {unit}\n"
            )

        # adaptive time window
        if "frequency_hits" in args.window_adaptation and not change_detected:
            if shared_resources.hits.value > args.hits:
                if (
                    True
                ): 
                    tmp = t_e - 3 * 1 / freq
                    t_s = tmp if tmp > 0 else 0
                    text += f"[bold purple][PREDICTOR] (#{shared_resources.count.value}):[/][green]Adjusting start time to {t_s} sec\n[/]"
            else:
                if not change_detected:
                    t_s = 0
                    if shared_resources.hits.value == 0:
                        text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/][red bold] Resetting start time to {t_s} sec\n[/]"
        elif "data" in args.window_adaptation and len(shared_resources.data) > 0 and not change_detected:
            text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/][green]Trying time window adaptation: {shared_resources.count.value:.0f} =? { args.hits * shared_resources.hits.value:.0f}\n[/]"
            if shared_resources.count.value == args.hits * shared_resources.hits.value:
                # t_s = shared_resources.data[-shared_resources.count.value]['t_start']
                # text += f'[bold purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] Adjusting start time to t_start {t_s} sec\n[/]'
                if len(shared_resources.t_flush) > 0:
                    print(shared_resources.t_flush)
                    index = int(args.hits * shared_resources.hits.value - 1)
                    t_s = shared_resources.t_flush[index]
                    text += f"[bold purple][PREDICTOR] (#{shared_resources.count.value}):[/][green]Adjusting start time to t_flush[{index}] {t_s} sec\n[/]"

    if not np.isnan(freq):
        samples = len(shared_resources.detector_frequencies)
        changes = shared_resources.detector_change_count.value
        recent_freqs = list(shared_resources.detector_frequencies)[-5:] if len(shared_resources.detector_frequencies) >= 5 else list(shared_resources.detector_frequencies)

        success_rate = (samples / prediction_count) * 100 if prediction_count > 0 else 0

        text += f"\n[bold cyan]{algorithm.upper()} ANALYSIS (Prediction #{prediction_count})[/]\n"
        text += f"[cyan]Frequency detections: {samples}/{prediction_count} ({success_rate:.1f}% success)[/]\n"
        text += f"[cyan]Pattern changes detected: {changes}[/]\n"
        text += f"[cyan]Current frequency: {freq:.3f} Hz ({1/freq:.2f}s period)[/]\n"

        if samples > 1:
            text += f"[cyan]Recent freq history: {[f'{f:.3f}Hz' for f in recent_freqs]}[/]\n"

            if len(recent_freqs) >= 2:
                trend = "increasing" if recent_freqs[-1] > recent_freqs[-2] else "decreasing" if recent_freqs[-1] < recent_freqs[-2] else "stable"
                text += f"[cyan]Frequency trend: {trend}[/]\n"

        text += f"[cyan]{algorithm.upper()} window size: {samples} samples[/]\n"
        text += f"[cyan]{algorithm.upper()} changes detected: {changes}[/]\n"

        text += f"[bold cyan]{'='*50}[/]\n\n"

    # TODO 1: Make sanity check -- see if the same number of bytes was transferred
    # TODO 2: Train a model to validate the predictions?
    text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Ended"
    shared_resources.start_time.value = t_s
    return text, change_detected, change_point_info


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
