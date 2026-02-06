"""
Change point detection algorithms for FTIO online predictor.

This module provides change_detection change point detection algorithms for detecting
I/O pattern changes in streaming data.
It includes ADWIN: Adaptive Windowing with Hoeffding bounds for statistical guarantees


Author: Amine Aherbil
Copyright (c) 2025 TU Darmstadt, Germany
Date: January 2025
Editor: Ahmad Tarraf

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from __future__ import annotations

from argparse import Namespace
from typing import Any

import numpy as np

from ftio.freq.helper import MyConsole
from ftio.freq.prediction import Prediction
from ftio.prediction.change_detection.helper import get_frequencies, get_timestamps
from ftio.prediction.helper import get_dominant
from ftio.prediction.shared_resources import SharedResources

CONSOLE = MyConsole()
CONSOLE.set(True)


class CUSUMDetector:
    """Adaptive-Variance CUSUM detector with variance-based threshold adaptation."""

    def __init__(
        self,
        window_size: int = 50,
        past_predictions=None,
        online_detection=None,
        verbose: bool = False,
    ):
        """Initialize AV-CUSUM detector with rolling window size (default: 50)."""
        self.window_size = window_size
        self.verbose = verbose
        CONSOLE.set(verbose)

        self.sum_pos = 0.0
        self.sum_neg = 0.0
        self.reference = None

        self.adaptive_threshold = 0.0
        self.adaptive_drift = 0.0
        self.rolling_std = 0.0
        # assign based on previous changes
        self.state = {}
        self.change_count = 0
        self.last_change_time = 0
        if online_detection:
            self.change_count = online_detection["change_count"]
            self.last_change_time = online_detection["last_change_time"]
            self.state = online_detection["state"]

        # assign based on predictions
        if past_predictions is None:
            shared_resources = SharedResources()
            past_predictions = list(shared_resources.data)

        self.frequencies = get_frequencies(past_predictions)
        self.timestamps = get_timestamps(past_predictions)

    def _update_adaptive_parameters(self):
        """Calculate thresholds automatically from data standard deviation."""

        all_frequencies = self.frequencies  # also includes most recent
        recent_frequencies = []
        if len(all_frequencies) > 1:
            recent_frequencies = all_frequencies[-self.window_size - 1 : -1]

        if self.verbose:
            CONSOLE.print(
                f"[dim magenta][CUSUM DEBUG] Buffer for σ calculation (excluding current): {[f'{f:.3f}' for f in recent_frequencies]} (len={len(recent_frequencies)})[/]"
            )

        if len(recent_frequencies) >= 3:
            self.rolling_std = np.std(np.array(recent_frequencies))
            std_factor = max(self.rolling_std, 0.01)
            self.adaptive_threshold = 2.0 * std_factor
            self.adaptive_drift = 0.5 * std_factor

            if self.verbose:
                CONSOLE.print(
                    f"[dim cyan][CUSUM] σ={self.rolling_std:.3f}, "
                    f"h_t={self.adaptive_threshold:.3f} (2σ threshold), "
                    f"k_t={self.adaptive_drift:.3f} (0.5σ drift)[/]"
                )

    def reset_cusum_state(self):
        """Reset CUSUM state when no frequency is detected."""
        self.last_change_time = 0
        self.state = {}
        self.sum_neg = 0
        self.sum_pos = 0

        CONSOLE.print(
            "[dim yellow][CUSUM] State cleared: Starting fresh when frequency resumes[/]"
        )

    def add_frequency(
        self, freq: float, timestamp: float = None
    ) -> tuple[bool, dict[str, Any]]:

        if np.isnan(freq) or freq <= 0:
            CONSOLE.print(
                "[yellow][AV-CUSUM] No frequency found - resetting algorithm state[/]"
            )
            self.reset_cusum_state()
            return False, {}

        self.frequencies.append(freq)
        self.timestamps.append(timestamp)

        self._update_adaptive_parameters()
        change_detected, change_info = self._detect_change(freq, timestamp)
        return change_detected, change_info

    def _detect_change(
        self, freq: float, timestamp: float = None
    ) -> tuple[bool, dict[str, Any]]:
        """
        Detect a change point in the frequency using AV-CUSUM.

        Updates cumulative sums, evaluates change detection, adapts the reference,
        resets the window if needed, and optionally prints debug info.

        Returns:
            change_detected (bool): True if a change point is detected.
            change_info (dict): Details about the detection, empty if none.
        """
        min_init_samples = 3
        change_info: dict[str, Any] = {}

        # Initialize reference if enough samples
        if len(self.frequencies) >= min_init_samples and self.reference is None:
            self.reference = np.mean(self.frequencies[:min_init_samples])
            CONSOLE.print(
                f"[cyan][AV-CUSUM] Reference established: {self.reference:.3f} Hz "
                f"(from first {min_init_samples} observations: "
                f"{[f'{f:.3f}' for f in self.frequencies[:min_init_samples]]})[/]"
            )

        # Early exit if not enough samples or invalid threshold
        if len(self.frequencies) < min_init_samples or self.adaptive_threshold <= 0:
            CONSOLE.print(
                f"[dim yellow][AV-CUSUM] Collecting calibration data "
                f"({len(self.frequencies)}/{min_init_samples})[/]"
            )
            return False, change_info

        # Compute deviation and update cumulative sums
        deviation = freq - self.reference
        self.sum_pos = max(0, self.sum_pos + deviation - self.adaptive_drift)
        self.sum_neg = max(0, self.sum_neg - deviation - self.adaptive_drift)

        # Optional debug output
        if self.verbose:
            current_window_size = len(self.frequencies)
            CONSOLE.print(
                f"[dim yellow][AV-CUSUM DEBUG] Observation #{current_window_size}:[/]\n"
                f"  [dim]• Current freq: {freq:.3f} Hz[/]\n"
                f"  [dim]• Reference: {self.reference:.3f} Hz[/]\n"
                f"  [dim]• Deviation: {deviation:.3f}[/]\n"
                f"  [dim]• Adaptive drift: {self.adaptive_drift:.3f} (k_t = 0.5×σ, σ={self.rolling_std:.3f})[/]\n"
                f"  [dim]• Sum_pos before: {self.sum_pos:.3f}[/]\n"
                f"  [dim]• Sum_neg before: {self.sum_neg:.3f}[/]\n"
                f"  [dim]• Adaptive threshold: {self.adaptive_threshold:.3f} (h_t = 2.0×σ, σ={self.rolling_std:.3f})[/]"
            )

        # Detect change
        change_detected = (
            self.sum_pos > self.adaptive_threshold
            or self.sum_neg > self.adaptive_threshold
        )
        change_type = (
            "increase"
            if self.sum_pos > self.adaptive_threshold
            else "decrease" if self.sum_neg > self.adaptive_threshold else "none"
        )
        change_percent = abs(deviation / self.reference * 100) if self.reference else 0

        # Build change info dict
        change_info = {
            "timestamp": timestamp,
            "frequency": freq,
            "reference": self.reference,
            "sum_pos": self.sum_pos,
            "sum_neg": self.sum_neg,
            "threshold": self.adaptive_threshold,
            "rolling_std": self.rolling_std,
            "deviation": deviation,
            "change_type": change_type,
        }

        if change_detected:
            old_reference = self.reference
            self.reference = freq

            CONSOLE.print(
                f"[bold yellow][AV-CUSUM] CHANGE DETECTED! {old_reference:.3f}Hz → {freq:.3f}Hz ({change_percent:.1f}% {change_type})[/]\n"
                f"[yellow][AV-CUSUM] Sum_pos={self.sum_pos:.2f}, Sum_neg={self.sum_neg:.2f}, Adaptive_Threshold={self.adaptive_threshold:.2f}[/]\n"
                f"[dim yellow]AV-CUSUM ANALYSIS: Cumulative sum exceeded change_detection threshold {self.adaptive_threshold:.2f}[/]\n"
                f"[dim yellow]Detection method: {'Positive sum (upward trend)' if self.sum_pos > self.adaptive_threshold else 'Negative sum (downward trend)'}[/]\n"
                f"[dim yellow]Adaptive drift: {self.adaptive_drift:.3f} (σ={self.rolling_std:.3f})[/]\n"
                f"[cyan][CUSUM] Reference updated: {old_reference:.3f} → {self.reference:.3f} Hz ({change_percent:.1f}% change)[/]"
            )

            # Reset sums and window
            self.sum_pos = 0.0
            self.sum_neg = 0.0

            old_window_size = len(self.frequencies)
            self.frequencies = [freq]
            self.timestamps = [timestamp or 0.0]

            CONSOLE.print(
                f"[green][CUSUM] CHANGE POINT ADAPTATION: Discarded {old_window_size - 1} past samples, starting fresh from current detection[/]\n"
                f"[green][CUSUM] WINDOW RESET: {old_window_size} → {len(self.frequencies)} samples[/]"
            )
            self.change_count += 1

        return change_detected, change_info


def detect_pattern_change_cusum(
    args: Namespace,
    shared_resources: SharedResources,
    current_prediction: Prediction,
    detector: CUSUMDetector,
    counter: int,
) -> tuple[bool, str | None, float, float | None, float | None]:
    """
    Detect frequency pattern changes using a CUSUM-based change point detector.

    This function processes the current prediction, updates the CUSUM detector
    state, and determines whether a statistically significant change in the
    dominant frequency has occurred.

    rgs:
       args (Namespace):
           Runtime configuration arguments. The `gui` flag controls whether
           change events are sent to the GUI logger.
       shared_resources (SharedResources):
           Shared state container used for online detection bookkeeping and
           inter-process communication.
       current_prediction (Prediction):
           The latest prediction object containing frequency and time
           information.
       detector (CUSUMDetector):
           The CUSUM change point detector instance maintaining internal
           cumulative sum state.
       counter (int):
           Monotonic counter indicating the number of processed predictions.
    """
    change_detected = False
    change_log = None
    reference = None

    current_freq = get_dominant(current_prediction)
    current_time = current_prediction.t_end
    new_start_time = current_prediction.t_start

    if not np.isnan(current_freq):
        change_detected, change_info = detector.add_frequency(current_freq, current_time)

        if change_detected:
            change_type = change_info["change_type"]
            reference = change_info["reference"]
            threshold = change_info["threshold"]
            sum_pos = change_info["sum_pos"]
            sum_neg = change_info["sum_neg"]

            magnitude = abs(current_freq - reference)
            percent_change = (magnitude / reference * 100) if reference > 0 else 0

            change_log = (
                f"[bold red][CUSUM] CHANGE DETECTED! "
                f"{reference:.1f}Hz → {current_freq:.1f}Hz "
                f"(Δ={magnitude:.1f}Hz, {percent_change:.1f}% {change_type}) "
                f"at sample {len(shared_resources.detector_frequencies)}, "
                f"time={current_time:.3f}s[/]\n"
                f"[red][CUSUM] CUSUM stats: sum_pos={sum_pos:.2f}, "
                f"sum_neg={sum_neg:.2f}, threshold={threshold}[/]\n"
                f"[red][CUSUM] Cumulative sum exceeded threshold -> "
                f"Starting fresh analysis[/]"
            )

            if percent_change > 100:
                min_window_size = 0.5
            elif percent_change > 50:
                min_window_size = 1.0
            else:
                min_window_size = 2.0

            new_start_time = max(0, current_time - min_window_size)

            if args.gui:
                try:
                    from ftio.prediction.online_analysis import get_socket_logger

                    logger = get_socket_logger()
                    if logger is not None:
                        logger.send_log(
                            "change_point",
                            "CUSUM Change Point Detected",
                            {
                                "algorithm": "CUSUM",
                                "detection_time": current_time,
                                "change_type": change_type,
                                "frequency": current_freq,
                                "reference": reference,
                                "magnitude": magnitude,
                                "percent_change": percent_change,
                                "threshold": threshold,
                                "counter": counter,
                            },
                        )
                except ImportError:
                    pass
    else:
        detector.reset_cusum_state()
    #     Ahmad: does not make sense to reset. class is discarded anyways

    # assign shared stuff (always consistent)
    shared_resources.online_detection["change_count"] = detector.change_count
    shared_resources.online_detection["last_change_time"] = detector.last_change_time
    shared_resources.online_detection["state"] = detector.state

    return change_detected, change_log, new_start_time, reference, current_freq
