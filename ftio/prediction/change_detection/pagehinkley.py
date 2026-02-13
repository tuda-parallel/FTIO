"""
Change point detection algorithms for FTIO online predictor.
Self-Tuning Page-Hinkley test for sequential change point detection

Author: Amine Aherbil
Editor: Ahmad Tarraf
Copyright (c) 2026 TU Darmstadt, Germany
Version: v0.0.7
Date: January 2025
Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE"""

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


class SelfTuningPageHinkleyDetector:
    """Self-Tuning Page-Hinkley detector with change_detection running mean baseline."""

    def __init__(
        self,
        window_size: int = 50,
        past_predictions=None,
        online_detection=None,
        verbose: bool = False,
    ):
        """Initialize STPH detector with rolling window size (default: 10)."""
        self.window_size = window_size
        self.verbose = verbose
        CONSOLE.set(verbose)

        self.adaptive_threshold = 0.0
        self.adaptive_delta = 0.0
        self.rolling_std = 0.0

        self.cumulative_sum_pos = 0.0
        self.cumulative_sum_neg = 0.0
        self.reference_mean = 0.0
        self.sum_of_samples = 0.0
        self.sample_count = 0
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

        # extract from state
        self.cumulative_sum_pos = self.state.get("cumulative_sum_pos", 0.0)
        self.cumulative_sum_neg = self.state.get("cumulative_sum_neg", 0.0)
        self.reference_mean = self.state.get("reference_mean", 0.0)
        self.sum_of_samples = self.state.get("sum_of_samples", 0.0)
        self.sample_count = self.state.get("sample_count", 0)
        CONSOLE.print(
            f"[green][PH DEBUG] Restored state: cusum_pos={self.cumulative_sum_pos:.3f}, cusum_neg={self.cumulative_sum_neg:.3f}, ref_mean={self.reference_mean:.3f}[/]"
        )

    def _update_adaptive_parameters(self, freq: float):
        """Calculate thresholds automatically from data standard deviation."""

        all_frequencies = self.frequencies  # also includes most recent
        recent_frequencies = []
        if len(all_frequencies) > 1:
            recent_frequencies = all_frequencies[-self.window_size - 1 : -1]

        if len(recent_frequencies) >= 3:
            self.rolling_std = np.std(np.array(recent_frequencies))
            std_factor = max(self.rolling_std, 0.01)
            self.adaptive_threshold = 2.0 * std_factor
            self.adaptive_delta = 0.5 * std_factor
            if self.verbose:
                CONSOLE.print(
                    f"[dim magenta][Page-Hinkley] σ={self.rolling_std:.3f}, "
                    f"λ_t={self.adaptive_threshold:.3f} (2σ threshold), "
                    f"δ_t={self.adaptive_delta:.3f} (0.5σ delta)[/]"
                )

    def add_frequency(
        self, freq: float, timestamp: float = None
    ) -> tuple[bool, float, dict[str, Any]]:

        if np.isnan(freq) or freq <= 0:
            CONSOLE.print(
                "[yellow][STPH] No frequency found - resetting Page-Hinkley state[/]"
            )
        self._update_adaptive_parameters(freq)
        self.frequencies.append(freq)
        self.timestamps.append(timestamp or 0.0)
        change_detected, triggering_sum, metadata = self._detect_change(freq)
        return change_detected, triggering_sum, metadata

    def _detect_change(self, freq: float) -> tuple[bool, float, dict[str, Any]]:
        change_detected = False
        triggering_sum = 0
        metadata = {}

        if np.isnan(freq) or freq <= 0:
            return change_detected, triggering_sum, metadata

        if self.sample_count == 0:
            self.sample_count = 1
            self.reference_mean = freq
            self.sum_of_samples = freq
            CONSOLE.print(
                f"[yellow][STPH] Reference mean initialized: {self.reference_mean:.3f} Hz[/]"
            )
        else:
            self.sample_count += 1
            self.sum_of_samples += freq
            self.reference_mean = self.sum_of_samples / self.sample_count

        pos_difference = freq - self.reference_mean - self.adaptive_delta
        old_cumsum_pos = self.cumulative_sum_pos
        self.cumulative_sum_pos = max(0, self.cumulative_sum_pos + pos_difference)

        neg_difference = self.reference_mean - freq - self.adaptive_delta
        old_cumsum_neg = self.cumulative_sum_neg
        self.cumulative_sum_neg = max(0, self.cumulative_sum_neg + neg_difference)

        if self.verbose:
            CONSOLE.print(
                f"[dim cyan][STPH DEBUG] Sample #{self.sample_count}:[/]\n"
                f"  [dim]• Current freq: {freq:.3f} Hz[/]\n"
                f"  [dim]• Reference mean: {self.reference_mean:.3f} Hz[/]\n"
                f"  [dim]• Adaptive delta: {self.adaptive_delta:.3f}[/]\n"
                f"  [dim]• Positive difference: "
                f"{freq:.3f} - {self.reference_mean:.3f} - {self.adaptive_delta:.3f} "
                f"= {pos_difference:.3f}[/]\n"
                f"  [dim]• Sum_pos = max(0, {old_cumsum_pos:.3f} + {pos_difference:.3f}) "
                f"= {self.cumulative_sum_pos:.3f}[/]\n"
                f"  [dim]• Negative difference: "
                f"{self.reference_mean:.3f} - {freq:.3f} - {self.adaptive_delta:.3f} "
                f"= {neg_difference:.3f}[/]\n"
                f"  [dim]• Sum_neg = max(0, {old_cumsum_neg:.3f} + {neg_difference:.3f}) "
                f"= {self.cumulative_sum_neg:.3f}[/]\n"
                f"  [dim]• Adaptive threshold: {self.adaptive_threshold:.3f}[/]\n"
                f"  [dim]• Upward change test: "
                f"{self.cumulative_sum_pos:.3f} > {self.adaptive_threshold:.3f} = "
                f"{'UPWARD CHANGE!' if self.cumulative_sum_pos > self.adaptive_threshold else 'No change'}[/]\n"
                f"  [dim]• Downward change test: "
                f"{self.cumulative_sum_neg:.3f} > {self.adaptive_threshold:.3f} = "
                f"{'DOWNWARD CHANGE!' if self.cumulative_sum_neg > self.adaptive_threshold else 'No change'}[/]"
            )

        self.state.update(
            {
                "cumulative_sum_pos": self.cumulative_sum_pos,
                "cumulative_sum_neg": self.cumulative_sum_neg,
                "reference_mean": self.reference_mean,
                "sum_of_samples": self.sum_of_samples,
                "sample_count": self.sample_count,
                "initialized": True,
            }
        )
        sample_count = len(self.frequencies)
        if sample_count < 3 or self.adaptive_threshold <= 0:
            return False, 0.0, {}

        upward_change = self.cumulative_sum_pos > self.adaptive_threshold
        downward_change = self.cumulative_sum_neg > self.adaptive_threshold
        change_detected = upward_change or downward_change

        if upward_change:
            change_type = "increase"
            triggering_sum = self.cumulative_sum_pos
        elif downward_change:
            change_type = "decrease"
            triggering_sum = self.cumulative_sum_neg
        else:
            change_type = "none"
            triggering_sum = max(self.cumulative_sum_pos, self.cumulative_sum_neg)

        if change_detected:
            magnitude = abs(freq - self.reference_mean)
            percent_change = (
                (magnitude / self.reference_mean * 100) if self.reference_mean > 0 else 0
            )

            CONSOLE.print(
                f"[bold cyan][STPH] CHANGE DETECTED! "
                f"{self.reference_mean:.3f}Hz → {freq:.3f}Hz "
                f"({percent_change:.1f}% {change_type})[/]\n"
                f"[cyan][STPH] Sum_pos={self.cumulative_sum_pos:.2f}, "
                f"Sum_neg={self.cumulative_sum_neg:.2f}, "
                f"Adaptive_Threshold={self.adaptive_threshold:.3f} "
                f"(σ={self.rolling_std:.3f})[/]\n"
                f"[dim cyan]STPH ANALYSIS: Cumulative sum exceeded change_detection "
                f"threshold {self.adaptive_threshold:.2f}[/]\n"
                f"[dim cyan]Detection method: "
                f"{'Positive sum (upward trend)' if upward_change else 'Negative sum (downward trend)'}[/]\n"
                f"[dim cyan]Adaptive minimum detectable change: "
                f"{self.adaptive_delta:.3f}[/]"
            )

            self.change_count += 1

        current_window_size = len(self.frequencies)

        metadata = {
            "cumulative_sum_pos": self.cumulative_sum_pos,
            "cumulative_sum_neg": self.cumulative_sum_neg,
            "triggering_sum": triggering_sum,
            "change_type": change_type,
            "reference_mean": self.reference_mean,
            "frequency": freq,
            "window_size": current_window_size,
            "threshold": self.adaptive_threshold,
            "adaptive_delta": self.adaptive_delta,
            "rolling_std": self.rolling_std,
        }

        return change_detected, triggering_sum, metadata


def detect_pattern_change_pagehinkley(
    args: Namespace,
    shared_resources: SharedResources,
    prediction: Prediction,
    detector: SelfTuningPageHinkleyDetector,
    counter: int,
) -> tuple[bool, str | None, float, float | None, float | None]:

    dominant_freq = get_dominant(prediction)
    current_time = prediction.t_end
    log_message = None
    reference_mean = None
    frequency = None

    if dominant_freq is None or np.isnan(dominant_freq):
        return False, None, prediction.t_start, None, None

    change_detected, triggering_sum, metadata = detector.add_frequency(
        dominant_freq, current_time
    )

    if change_detected:
        change_type = metadata.get("change_type", "unknown")
        frequency = metadata.get("frequency", dominant_freq)
        reference_mean = metadata.get("reference_mean", 0.0)
        window_size = metadata.get("window_size", 0)

        magnitude = abs(frequency - reference_mean)
        percent_change = (magnitude / reference_mean * 100) if reference_mean > 0 else 0

        direction_arrow = (
            "increasing"
            if change_type == "increase"
            else "decreasing" if change_type == "decrease" else "stable"
        )
        log_message = (
            f"[bold red][Page-Hinkley] PAGE-HINKLEY CHANGE DETECTED! {direction_arrow} "
            f"{reference_mean:.1f}Hz → {frequency:.1f}Hz "
            f"(Δ={magnitude:.1f}Hz, {percent_change:.1f}% {change_type}) "
            f"at sample {window_size}, time={current_time:.3f}s[/]\n"
            f"[red][Page-Hinkley] Page-Hinkley stats: sum_pos={metadata.get('cumulative_sum_pos', 0):.2f}, "
            f"sum_neg={metadata.get('cumulative_sum_neg', 0):.2f}, threshold={detector.adaptive_threshold:.3f}[/]\n"
            f"[red][Page-Hinkley] Cumulative sum exceeded threshold -> Starting fresh analysis[/]"
        )

        adaptive_start_time = current_time
        detector.last_change_time = current_time

        if args.gui:
            try:
                from ftio.prediction.online_analysis import get_socket_logger

                logger = get_socket_logger()
                if logger is not None:
                    logger.send_log(
                        "change_point",
                        "Page-Hinkley Change Point Detected",
                        {
                            "algorithm": "PageHinkley",
                            "frequency": frequency,
                            "reference_mean": reference_mean,
                            "magnitude": magnitude,
                            "percent_change": percent_change,
                            "triggering_sum": triggering_sum,
                            "change_type": change_type,
                            "position": window_size,
                            "timestamp": current_time,
                            "threshold": detector.adaptive_threshold,
                            "delta": detector.adaptive_delta,
                            "prediction_counter": counter,
                        },
                    )
            except ImportError:
                pass

    else:
        adaptive_start_time = prediction.t_start
        change_detected = False

    # assign shared stuff (always consistent)
    shared_resources.online_detection["change_count"] = detector.change_count
    shared_resources.online_detection["last_change_time"] = detector.last_change_time
    shared_resources.online_detection["state"] = detector.state

    return change_detected, log_message, adaptive_start_time, reference_mean, frequency
