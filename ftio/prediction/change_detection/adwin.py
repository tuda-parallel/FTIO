"""
Change point detection algorithms for FTIO online predictor.

This module provides change_detection change point detection algorithms for detecting
I/O pattern changes in streaming data.
It includes ADWIN: Adaptive Windowing with Hoeffding bounds for statistical guarantees

Author: Amine Aherbil
Editor: Ahmad Tarraf
Copyright (c) 2026 TU Darmstadt, Germany
Version: v0.0.7
Date: January 2025
Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE"""

from __future__ import annotations

import math
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


class AdwinDetector:
    """ADWIN detector for I/O pattern changes with automatic window sizing."""

    def __init__(
        self,
        delta: float = 0.05,
        past_predictions=None,
        online_detection=None,
        verbose: bool = False,
    ):
        """Initialize ADWIN detector with confidence parameter delta (default: 0.05)."""
        self.min_window_size = 2
        self.verbose = verbose
        CONSOLE.set(verbose)
        # assign default values
        self.delta = min(max(delta, 1e-12), 1 - 1e-12)
        self.last_change_point: int | None = None

        # assign based on previous changes
        self.change_count = 0
        self.last_change_time = 0
        if online_detection:
            self.change_count = online_detection["change_count"]
            self.last_change_time = online_detection["last_change_time"]

        # assign based on predictions
        if past_predictions is None:
            shared_resources = SharedResources()
            past_predictions = list(shared_resources.data)

        self.frequencies_found = len(past_predictions)
        self.frequencies = get_frequencies(past_predictions)
        self.timestamps = get_timestamps(past_predictions)
        self.state = {}

        if verbose:
            CONSOLE.print(
                f"[green][ADWIN] Initialized with δ={delta:.3f} "
                f"({(1 - delta) * 100:.0f}% confidence) [/]"
            )

    def _reset_window(self):
        self.frequencies_found = 0
        self.last_change_time = 0
        self.state = {}

        CONSOLE.print(
            "[dim yellow][ADWIN] Window cleared: No frequency data to analyze[/]"
        )

    def add_prediction(
        self,
        prediction: Prediction,
        timestamp: float = None,
    ) -> tuple[int, float] | None:

        freq = get_dominant(prediction)
        if timestamp is None:
            timestamp = prediction.t_end

        if np.isnan(freq) or freq <= 0:
            CONSOLE.print(
                "[yellow][ADWIN] No frequency found - resetting window history[/]"
            )
            self._reset_window()
            return None

        # create snapshot of the current prediction
        self.frequencies.append(freq)
        self.timestamps.append(timestamp)
        self.frequencies_found += 1

        if len(self.frequencies) < self.min_window_size:
            return None

        change_point = self._detect_change()

        if change_point is not None:
            exact_change_timestamp = self.timestamps[change_point]
            self._process_change_point(change_point)
            self.change_count += 1

            return change_point, exact_change_timestamp

        return None

    def _detect_change(self) -> int | None:

        n = len(self.frequencies)
        if n < 2 * self.min_window_size:
            return None

        for cut in range(self.min_window_size, n - self.min_window_size + 1):
            if self._test_cut_point(cut):
                CONSOLE.print(
                    f"[blue][ADWIN] Change detected at position {cut}/{n}, "
                    f"time={self.timestamps[cut]:.3f}s[/]"
                )
                return cut

        return None

    def _test_cut_point(self, cut: int) -> bool:
        """
        Test whether a given cut point represents a statistically significant
        change in the frequency stream using the ADWIN criterion.

        The method splits the frequency window into two segments at `cut`,
        computes their means, and checks whether the absolute mean difference
        exceeds an change_detection threshold derived from the confidence parameter
        `delta` and the harmonic mean of the segment sizes.

        Args:
            cut (int): Index at which to split the frequency window.

        Returns:
            bool: True if a change point is detected at the given cut, False otherwise.
        """

        # Split window
        left_data = self.frequencies[:cut]
        right_data = self.frequencies[cut:]

        n0 = len(left_data)
        n1 = len(right_data)

        if n0 <= 0 or n1 <= 0:
            return False

        mean0 = np.mean(left_data)
        mean1 = np.mean(right_data)
        mean_diff = abs(mean1 - mean0)

        # Harmonic mean of sample sizes
        n_harmonic = (n0 * n1) / (n0 + n1)

        try:
            confidence_term = math.log(2.0 / self.delta) / (2.0 * n_harmonic)
            threshold = math.sqrt(2.0 * confidence_term)
        except (ValueError, ZeroDivisionError):
            confidence_term = 0.0
            threshold = 0.05

        # test
        # threshold = threshold / 10

        if self.verbose:
            CONSOLE.print(
                "[blue][PREDICTOR: ADWIN] Cut={cut}[/]\n"
                f"  [dim]• Left window: {n0} samples, mean={mean0:.3f} Hz[/]\n"
                f"  [dim]• Right window: {n1} samples, mean={mean1:.3f} Hz[/]\n"
                f"  [dim]• Mean difference: |{mean1:.3f} − {mean0:.3f}| = {mean_diff:.3f}[/]\n"
                f"  [dim]• Harmonic mean: {n_harmonic:.1f}[/]\n"
                f"  [dim]• Confidence term: log(2/{self.delta}) / (2×{n_harmonic:.1f}) = {confidence_term:.6f}[/]\n"
                f"  [dim]• Threshold: √(2×{confidence_term:.6f}) = {threshold:.3f}[/]\n"
                f"  [dim]• Test: {mean_diff:.3f} > {threshold:.3f} ? "
                f"{'CHANGE!' if mean_diff > threshold else 'No change'}[/]"
            )

        return mean_diff > threshold

    def _process_change_point(self, change_point: int):
        """
        Apply a detected change point by trimming the historical frequency
        window and updating change-point metadata.

        The method:
        - Records the change point index
        - Updates the last change time
        - Shrinks the frequency and timestamp windows
        - Logs window adaptation statistics

        Args:
            change_point (int): Index at which the change was detected.
        """
        self.last_change_point = change_point
        change_time = self.timestamps[change_point]
        self.last_change_time = change_time if change_time is not None else 0.0

        old_window_size = len(self.frequencies)
        old_freq = np.mean(self.frequencies[:change_point]) if change_point > 0 else 0.0

        # Trim window in-place (keep same list object)
        frequencies = self.frequencies[change_point:]
        timestamps = self.timestamps[change_point:]

        new_window_size = len(frequencies)
        new_freq = np.mean(frequencies) if frequencies else 0.0

        freq_change = abs(new_freq - old_freq) / old_freq * 100.0 if old_freq > 0 else 0.0
        time_span = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0.0

        CONSOLE.print(
            "[green][ADWIN] Window adapted:[/] "
            f"{old_window_size} → {new_window_size} samples\n"
            "[green][ADWIN] Frequency shift:[/] "
            f"{old_freq:.3f} → {new_freq:.3f} Hz ({freq_change:.1f}%)\n"
            "[green][ADWIN] New window span:[/] "
            f"{time_span:.2f} seconds"
        )

    def get_adaptive_start_time(
        self, current_prediction: Prediction, timestamps
    ) -> float:
        """
        Compute an change_detection start time for the next FTIO window based on
        the most recent detected change point.

        The start time is constrained by a minimum window size and a
        maximum lookback period to ensure stable predictions.

        Args:
            current_prediction (Prediction): The current prediction object.

        Returns:
            float: Adaptive window start time.
        """
        if not timestamps:
            return current_prediction.t_start

        last_change_time = self.last_change_time
        if last_change_time is not None:
            min_window = 0.5
            max_lookback = 10.0

            window_span = current_prediction.t_end - last_change_time

            if window_span < min_window:
                adaptive_start = max(0.0, current_prediction.t_end - min_window)
                CONSOLE.print(
                    "[yellow][ADWIN] Change point too recent, using min window:[/] "
                    f"{adaptive_start:.6f}s"
                )
            elif window_span > max_lookback:
                adaptive_start = max(0.0, current_prediction.t_end - max_lookback)
                CONSOLE.print(
                    "[yellow][ADWIN] Change point too old, using max lookback:[/] "
                    f"{adaptive_start:.6f}s"
                )
            else:
                adaptive_start = last_change_time
                CONSOLE.print(
                    "[green][ADWIN] Using EXACT change point timestamp:[/] "
                    f"{adaptive_start:.6f}s (window span: {window_span:.3f}s)"
                )

            return adaptive_start

        # Fallback: use earliest timestamp with bounds
        window_start = timestamps[0]
        min_start = current_prediction.t_end - 10.0
        max_start = current_prediction.t_end - 0.5

        return max(min_start, min(window_start, max_start))

    def get_window_stats(self, frequencies, timestamps) -> dict[str, Any]:
        """
        Return current ADWIN window statistics for debugging and logging.

        Summarizes the active frequency window used by the change detector.
        """
        total_samples = self.frequencies_found
        change_count = self.change_count

        size = len(frequencies)
        mean = float(np.mean(frequencies)) if frequencies else 0.0
        std = float(np.std(frequencies)) if frequencies else 0.0
        value_range = (
            [float(np.min(frequencies)), float(np.max(frequencies))]
            if frequencies
            else [0.0, 0.0]
        )
        time_span = float(timestamps[-1] - timestamps[0]) if len(timestamps) > 1 else 0.0

        return {
            "size": size,
            "mean": mean,
            "std": std,
            "range": value_range,
            "time_span": time_span,
            "total_samples": total_samples,
            "change_count": change_count,
        }

    def log_change_point(
        self, counter: int, old_freq: float, new_freq: float, stats
    ) -> str:

        last_change_time = self.last_change_time
        if last_change_time is None:
            return ""

        freq_change_pct = abs(new_freq - old_freq) / old_freq * 100 if old_freq > 0 else 0

        log_msg = (
            f"[red bold][CHANGE_POINT] t_s={last_change_time:.3f} sec[/]\n"
            f"[purple][PREDICTOR] (#{counter}):[/][yellow] "
            f"ADWIN detected pattern change: {old_freq:.3f} → {new_freq:.3f} Hz "
            f"({freq_change_pct:.1f}% change)[/]\n"
            f"[purple][PREDICTOR] (#{counter}):[/][yellow] "
            f"Adaptive window: {stats['size']} samples, "
            f"span={stats['time_span']:.1f}s, "
            f"changes={stats['change_count']}/{stats['total_samples']}[/]\n"
            f"[dim blue]ADWIN ANALYSIS: Statistical significance detected using Hoeffding bounds[/]\n"
            f"[dim blue]Window split analysis found mean difference > confidence threshold[/]\n"
            f"[dim blue]Confidence level: {(1 - self.delta) * 100:.0f}% (δ={self.delta:.3f})[/]"
        )

        self.last_change_point = None

        return log_msg


def detect_pattern_change_adwin(
    args: Namespace,
    shared_resources: SharedResources,
    current_prediction: Prediction,
    detector: AdwinDetector,
    counter: int,
) -> tuple[bool, str | None, float, float | None, float | None]:

    change_detected = False
    new_start_time = current_prediction.t_start
    change_log, old_freq, current_freq = None, None, None

    change_point = detector.add_prediction(current_prediction)
    if change_point is not None:
        change_detected = True
        change_idx, change_time = change_point

        current_freq = get_dominant(current_prediction)
        old_freq = current_freq  # fallback if no history

        window_stats = detector.get_window_stats(
            detector.frequencies, detector.timestamps
        )
        if len(detector.frequencies) > 1:
            old_freq = max(0.1, window_stats["mean"] * 0.9)

        change_log = detector.log_change_point(
            counter, old_freq, current_freq, window_stats
        )

        new_start_time = detector.get_adaptive_start_time(
            current_prediction, detector.timestamps
        )

        if args.gui:
            try:
                from ftio.gui.socket_logger import get_socket_logger

                logger = get_socket_logger()
                if logger is not None:
                    logger.send_log(
                        "change_point",
                        "ADWIN Change Point Detected",
                        {
                            "exact_time": change_time,
                            "old_freq": old_freq,
                            "new_freq": current_freq,
                            "adaptive_start": new_start_time,
                            "counter": counter,
                        },
                    )
            except ImportError:
                pass

        # assign shared stuff:
        shared_resources.online_detection["change_count"] = detector.change_count
        shared_resources.online_detection["last_change_time"] = detector.last_change_time
        shared_resources.online_detection["state"] = detector.state

    return change_detected, change_log, new_start_time, old_freq, current_freq
