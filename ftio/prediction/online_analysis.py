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
from ftio.plot.plot_bandwidth import plot_bar_with_rich
from ftio.plot.units import set_unit
from ftio.prediction.helper import get_dominant
from ftio.prediction.shared_resources import SharedResources
from ftio.prediction.change_point_detection import ChangePointDetector, detect_pattern_change_adwin, CUSUMDetector, detect_pattern_change_cusum, SelfTuningPageHinkleyDetector, detect_pattern_change_pagehinkley

# ADWIN change point detection is now handled by the ChangePointDetector class
# from ftio.prediction.change_point_detection import detect_pattern_change


class SocketLogger:
    """Socket client to send logs to GUI visualizer"""
    
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
        """Send log message to GUI"""
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
        """Close socket connection"""
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False


_socket_logger = None
# Removed _detector_cache - using shared_resources instead

def get_socket_logger():
    """Get or create socket logger instance"""
    global _socket_logger
    if _socket_logger is None:
        _socket_logger = SocketLogger()
    return _socket_logger

def strip_rich_formatting(text: str) -> str:
    """Remove Rich console formatting while preserving message content"""
    import re
    
    clean_text = re.sub(r'\[/?(?:purple|blue|green|yellow|red|bold|dim|/)\]', '', text)
    
    clean_text = re.sub(r'\[(?:purple|blue|green|yellow|red|bold|dim)\[', '[', clean_text)
    
    return clean_text

def log_to_gui_and_console(console: Console, message: str, log_type: str = "info", data: dict = None):
    """Print to console AND send to GUI via socket"""
    logger = get_socket_logger()
    clean_message = strip_rich_formatting(message)
    
    console.print(message)
    
    logger.send_log(log_type, clean_message, data)


def get_change_detector(shared_resources: SharedResources, algorithm: str = "adwin"):
    """Get or create the change point detector instance with shared state.
    
    Args:
        shared_resources: Shared state for multiprocessing
        algorithm: Algorithm to use ("adwin", "cusum", or "ph")
    """
    console = Console()
    algo = (algorithm or "adwin").lower()

    # Use local module-level cache for detector instances (per process)
    # And shared flags to control initialization messages
    global _local_detector_cache
    if '_local_detector_cache' not in globals():
        _local_detector_cache = {}
    
    detector_key = f"{algo}_detector"
    init_flag_attr = f"{algo}_initialized"
    
    # Check if detector already exists in this process
    if detector_key in _local_detector_cache:
        return _local_detector_cache[detector_key]

    # Check if this is the first initialization across all processes
    init_flag = getattr(shared_resources, init_flag_attr)
    show_init_message = not init_flag.value
    
    # console.print(f"[dim yellow][DETECTOR CACHE] Creating new {algo.upper()} detector[/]")
    
    if algo == "cusum":
        # Parameter-free CUSUM: thresholds calculated automatically from data (2σ rule, 50-sample window)
        detector = CUSUMDetector(window_size=50, shared_resources=shared_resources, show_init=show_init_message, verbose=True)
    elif algo == "ph":
        # Parameter-free Page-Hinkley: thresholds calculated automatically from data (5σ rule)
        detector = SelfTuningPageHinkleyDetector(shared_resources=shared_resources, show_init=show_init_message, verbose=True)
    else:
        # ADWIN: only theoretical δ=0.05 (95% confidence)
        detector = ChangePointDetector(delta=0.05, shared_resources=shared_resources, show_init=show_init_message, verbose=True)

    # Store detector in local cache and mark as initialized globally
    _local_detector_cache[detector_key] = detector
    init_flag.value = True
    # console.print(f"[dim blue][DETECTOR CACHE] Stored {algo.upper()} detector in local cache[/]")
    return detector

def ftio_process(shared_resources: SharedResources, args: list[str], msgs=None) -> None:
    """
    Perform one FTIO prediction and send a single structured message to the GUI.
    Detects change points using the text produced by window_adaptation().
    """
    console = Console()
    pred_id = shared_resources.count.value

    # Start log
    start_msg = f"[purple][PREDICTOR] (#{pred_id}):[/] Started"
    log_to_gui_and_console(console, start_msg, "predictor_start", {"count": pred_id})

    # run FTIO core
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{shared_resources.start_time.value:.2f}"])
    prediction_list, parsed_args = ftio_core.main(args, msgs)
    if not prediction_list:
        log_to_gui_and_console(console,
            "[yellow]Terminating prediction (no data passed)[/]",
            "termination", {"reason": "no_data"})
        return

    prediction = prediction_list[-1]
    freq = get_dominant(prediction) or 0.0

    # save internal data
    save_data(prediction, shared_resources)

    # build console output
    text = display_result(freq, prediction, shared_resources)
    # window_adaptation logs change points in its text
    text += window_adaptation(parsed_args, prediction, freq, shared_resources)

    # ---------- Detect if a change point was logged ----------
    is_change_point = "[CHANGE_POINT]" in text
    change_point_info = None
    if is_change_point:
        # try to extract start time and old/new frequency if mentioned
        import re
        t_match = re.search(r"t_s=([0-9.]+)", text)
        f_match = re.search(r"change:\s*([0-9.]+)\s*→\s*([0-9.]+)", text)
        change_point_info = {
            "prediction_id": pred_id,
            "timestamp": float(prediction.t_end),
            "old_frequency": float(f_match.group(1)) if f_match else 0.0,
            "new_frequency": float(f_match.group(2)) if f_match else freq,
            "start_time": float(t_match.group(1)) if t_match else float(prediction.t_start)
        }

    # ---------- Build structured prediction for GUI ----------
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

    # ---------- Send to dashboard and print to console ----------
    get_socket_logger().send_log("prediction", "FTIO structured prediction", structured_prediction)
    log_to_gui_and_console(console, text, "prediction_log", {"count": pred_id, "freq": dominant_freq})

    # increase counter for next prediction
    shared_resources.count.value += 1



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
    text = ""
    t_s = prediction.t_start
    t_e = prediction.t_end
    total_bytes = prediction.total_bytes

    # Simple prediction counter without phase tracking
    prediction_count = shared_resources.count.value
    text += f"Prediction #{prediction_count}\n"

    text += hits(args, prediction, shared_resources)

    # Use the algorithm specified in command-line arguments
    algorithm = args.algorithm  # Now gets from CLI (--algorithm adwin/cusum)

    detector = get_change_detector(shared_resources, algorithm)
    
    # Call appropriate change detection algorithm
    if algorithm == "cusum":
        change_detected, change_log, adaptive_start_time = detect_pattern_change_cusum(
            shared_resources, prediction, detector, shared_resources.count.value
        )
    elif algorithm == "ph":
        change_detected, change_log, adaptive_start_time = detect_pattern_change_pagehinkley(
            shared_resources, prediction, detector, shared_resources.count.value
        )
    else:
        # Default ADWIN (your existing implementation)
        change_detected, change_log, adaptive_start_time = detect_pattern_change_adwin(
            shared_resources, prediction, detector, shared_resources.count.value
        )
    
    # Add informative logging for no frequency cases
    if np.isnan(freq):
        if algorithm == "cusum":
            cusum_samples = len(shared_resources.cusum_frequencies)
            cusum_changes = shared_resources.cusum_change_count.value
            text += f"[dim][CUSUM STATE: {cusum_samples} samples, {cusum_changes} changes detected so far][/]\n"
            if cusum_samples > 0:
                last_freq = shared_resources.cusum_frequencies[-1] if shared_resources.cusum_frequencies else "None"
                text += f"[dim][LAST KNOWN FREQ: {last_freq:.3f} Hz][/]\n"
        elif algorithm == "ph":
            ph_samples = len(shared_resources.pagehinkley_frequencies)
            ph_changes = shared_resources.pagehinkley_change_count.value
            text += f"[dim][PAGE-HINKLEY STATE: {ph_samples} samples, {ph_changes} changes detected so far][/]\n"
            if ph_samples > 0:
                last_freq = shared_resources.pagehinkley_frequencies[-1] if shared_resources.pagehinkley_frequencies else "None"
                text += f"[dim][LAST KNOWN FREQ: {last_freq:.3f} Hz][/]\n"
        else:  # ADWIN
            adwin_samples = len(shared_resources.adwin_frequencies)
            adwin_changes = shared_resources.adwin_change_count.value
            text += f"[dim][ADWIN STATE: {adwin_samples} samples, {adwin_changes} changes detected so far][/]\n"
            if adwin_samples > 0:
                last_freq = shared_resources.adwin_frequencies[-1] if shared_resources.adwin_frequencies else "None"
                text += f"[dim][LAST KNOWN FREQ: {last_freq:.3f} Hz][/]\n"
    
    if change_detected and change_log:
        text += f"{change_log}\n"
        # Ensure adaptive start time maintains sufficient window for analysis
        min_window_size = 1.0 
        
        # Conservative adaptation: only adjust if the new window is significantly larger than minimum
        safe_adaptive_start = min(adaptive_start_time, t_e - min_window_size)
        
        # Additional safety: ensure we have at least min_window_size of data
        if safe_adaptive_start >= 0 and (t_e - safe_adaptive_start) >= min_window_size:
            t_s = safe_adaptive_start
            algorithm_name = args.algorithm.upper() if hasattr(args, 'algorithm') else "UNKNOWN"
            text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] {algorithm_name} adapted window to start at {t_s:.3f}s (window size: {t_e - t_s:.3f}s)[/]\n"
        else:
            # Conservative fallback: keep a reasonable window size
            t_s = max(0, t_e - min_window_size)
            algorithm_name = args.algorithm.upper() if hasattr(args, 'algorithm') else "UNKNOWN"
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

        # adaptive time window (original frequency_hits method)
        if "frequency_hits" in args.window_adaptation and not change_detected:
            if shared_resources.hits.value > args.hits:
                if (
                    True
                ): 
                    tmp = t_e - 3 * 1 / freq
                    t_s = tmp if tmp > 0 else 0
                    text += f"[bold purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] Adjusting start time to {t_s} sec\n[/]"
            else:
                if not change_detected:  # Don't reset if we detected a change point
                    t_s = 0
                    if shared_resources.hits.value == 0:
                        text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/][red bold] Resetting start time to {t_s} sec\n[/]"
        elif "data" in args.window_adaptation and len(shared_resources.data) > 0 and not change_detected:
            text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] Trying time window adaptation: {shared_resources.count.value:.0f} =? { args.hits * shared_resources.hits.value:.0f}\n[/]"
            if shared_resources.count.value == args.hits * shared_resources.hits.value:
                # t_s = shared_resources.data[-shared_resources.count.value]['t_start']
                # text += f'[bold purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] Adjusting start time to t_start {t_s} sec\n[/]'
                if len(shared_resources.t_flush) > 0:
                    print(shared_resources.t_flush)
                    index = int(args.hits * shared_resources.hits.value - 1)
                    t_s = shared_resources.t_flush[index]
                    text += f"[bold purple][PREDICTOR] (#{shared_resources.count.value}):[/][green] Adjusting start time to t_flush[{index}] {t_s} sec\n[/]"

    # TODO 1: Make sanity check -- see if the same number of bytes was transferred
    # TODO 2: Train a model to validate the predictions?
    
    # Show detailed analysis every time there's a dominant frequency prediction
    if not np.isnan(freq):
        if algorithm == "cusum":
            samples = len(shared_resources.cusum_frequencies)
            changes = shared_resources.cusum_change_count.value
            recent_freqs = list(shared_resources.cusum_frequencies)[-5:] if len(shared_resources.cusum_frequencies) >= 5 else list(shared_resources.cusum_frequencies)
        elif algorithm == "ph":
            samples = len(shared_resources.pagehinkley_frequencies)
            changes = shared_resources.pagehinkley_change_count.value
            recent_freqs = list(shared_resources.pagehinkley_frequencies)[-5:] if len(shared_resources.pagehinkley_frequencies) >= 5 else list(shared_resources.pagehinkley_frequencies)
        else:  # ADWIN
            samples = len(shared_resources.adwin_frequencies)
            changes = shared_resources.adwin_change_count.value
            recent_freqs = list(shared_resources.adwin_frequencies)[-5:] if len(shared_resources.adwin_frequencies) >= 5 else list(shared_resources.adwin_frequencies)
        
        success_rate = (samples / prediction_count) * 100 if prediction_count > 0 else 0
        
        text += f"\n[bold cyan]{algorithm.upper()} ANALYSIS (Prediction #{prediction_count})[/]\n"
        text += f"[cyan]Frequency detections: {samples}/{prediction_count} ({success_rate:.1f}% success)[/]\n"
        text += f"[cyan]Pattern changes detected: {changes}[/]\n"
        text += f"[cyan]Current frequency: {freq:.3f} Hz ({1/freq:.2f}s period)[/]\n"
        
        if samples > 1:
            text += f"[cyan]Recent freq history: {[f'{f:.3f}Hz' for f in recent_freqs]}[/]\n"
            
            # Show frequency trend
            if len(recent_freqs) >= 2:
                trend = "increasing" if recent_freqs[-1] > recent_freqs[-2] else "decreasing" if recent_freqs[-1] < recent_freqs[-2] else "stable"
                text += f"[cyan]Frequency trend: {trend}[/]\n"
        
        # Show window status
        text += f"[cyan]{algorithm.upper()} window size: {samples} samples[/]\n"
        text += f"[cyan]{algorithm.upper()} changes detected: {changes}[/]\n"
        
        text += f"[bold cyan]{'='*50}[/]\n\n"
    
    text += f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Ended"
    shared_resources.start_time.value = t_s
    return text


def save_data(prediction, shared_resources) -> None:
    """Put all data from `prediction` in a `queue`. The total bytes are as well saved here.

    Args:
        prediction (dict): result from FTIO
        shared_resources (SharedResources): shared resources among processes
    """
    shared_resources.aggregated_bytes.value += prediction.total_bytes

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
    # Dominant frequency with context
    if not np.isnan(freq):
        text = f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Dominant freq {freq:.3f} Hz ({1/freq if freq != 0 else 0:.2f} sec)\n"
    else:
        text = f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] No dominant frequency found\n"

    # Candidates with better formatting
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
