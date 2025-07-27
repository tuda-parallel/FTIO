"""
This file provides functions for periodicity analysis in frequency data using various methods,
including Recurrence Period Density Entropy, Spectral Flatness, Correlation, Correlation of Individual Periods, and Peak Sharpness.

Author: Anton Holderied
Copyright (c) 2025 TU Darmstadt, Germany
Date: Jul 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from __future__ import annotations

import matplotlib.pyplot as plt

# all
import numpy as np
from kneed import KneeLocator
from rich.panel import Panel
from concurrent.futures import ThreadPoolExecutor, as_completed


# find_peaks
from scipy.signal import find_peaks
from scipy.stats import kurtosis
from sklearn.cluster import DBSCAN
from sklearn.neighbors import KDTree

# Isolation forest
from sklearn.ensemble import IsolationForest

# Lof
from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors

from ftio.analysis._correlation import correlation
from ftio.plot.anomaly_plot import plot_decision_boundaries, plot_outliers
from ftio.plot.cepstrum_plot import plot_cepstrum


def new_periodicity_scores(
    amp: np.ndarray,
    signal: np.ndarray,
    prediction,
    args,
    peak_window_half_width: int = 3,
) -> str:

    def compute_peak_sharpness(
        spectrum_amp: np.ndarray,
        peak_indices_in_spectrum: np.ndarray,
        window_half_width: int,
    ) -> float:
        """
        Computes the average peak sharpness (excess kurtosis) for specified peak regions.
        Higher values indicate more peaked regions.
        """
        sharpness_scores = []
        for peak_idx in peak_indices_in_spectrum:
            start_idx = max(0, peak_idx - window_half_width)
            end_idx = min(len(spectrum_amp), peak_idx + window_half_width + 1)
            peak_window_spectrum = spectrum_amp[start_idx:end_idx]
            if peak_window_spectrum.size < 4:
                sharpness_scores.append(-2.0)
                continue
            if np.std(peak_window_spectrum) < 1e-9:
                sharpness_scores.append(-2.0)
                continue
            k = kurtosis(peak_window_spectrum, fisher=True, bias=False)
            sharpness_scores.append(k)
        if not sharpness_scores:
            return -2.0

        return float(np.mean(sharpness_scores))

    def compute_rpde(freq_arr: np.ndarray) -> float:
        safe_array = np.where(freq_arr <= 0, 1e-12, freq_arr)
        sum = np.sum(safe_array * np.log(safe_array))
        max = np.log(safe_array.size)
        rpde_score = 1 - (np.divide(sum, -max))
        return rpde_score

    def compute_spectral_flatness(freq_arr: np.ndarray) -> float:
        safe_spectrum = np.where(freq_arr <= 0, 1e-12, freq_arr)
        geometric_mean = np.exp(np.mean(np.log(safe_spectrum)))
        arithmetic_mean = np.mean(safe_spectrum)
        spectral_flatness_score = 1 - float((geometric_mean / arithmetic_mean))
        return spectral_flatness_score

    def signal_correlation(
        freq: float,
        sampling_rate: float,
        signal: np.ndarray,
        phi: float,
        start_time: float,
        text: str = "",
    ) -> float:
        dt = 1 / sampling_rate
        t = start_time + dt * np.arange(len(signal))
        waveform = np.cos(2 * np.pi * freq * t + phi)

        correlation_result = correlation(waveform, signal)
        return correlation_result

    def ind_period_correlation(
        freq: float,
        sampling_rate: float,
        signal: np.ndarray,
        phi: float,
        start_time: float,
        text: str = "",
    ) -> float:
        dt = 1 / sampling_rate
        t = start_time + dt * np.arange(len(signal))
        waveform = np.cos(2 * np.pi * freq * t + phi)

        period = 1 / freq
        phase_offset = phi / (2 * np.pi * freq)
        i = 0
        while True:
            center_time = (i * period) - start_time - phase_offset
            begin = round((center_time - 0.5 * period) * sampling_rate)
            end = round((center_time + 0.5 * period) * sampling_rate)
            if end < 1:
                i += 1
                continue
            begin = max(begin, 0)
            end = min(end, len(signal) - 1)
            correlation_result = correlation(waveform[begin:end], signal[begin:end])
            text += (
                f"[green]Correlation for period {i:3d} with indices {begin:5d},{end:5d}: "
                f"[black]{correlation_result:.4f} \n"
            )
            if end >= len(signal) - 1:
                break
            i += 1
        return text

    def parallel_period_correlation(
        freq: float,
        sampling_rate: float,
        signal: np.ndarray,
        phi: float,
        start_time: float,
        workers: int,
        text: str = "",
    ) -> str:
        dt = 1 / sampling_rate
        t = start_time + dt * np.arange(len(signal))
        waveform = np.cos(2 * np.pi * freq * t + phi)

        period = 1 / freq
        phase_offset = phi / (2 * np.pi * freq)

        # Precompute all (begin, end, i) intervals
        intervals = []
        i = 0
        while True:
            center_time = (i * period) - start_time - phase_offset
            begin = round((center_time - 0.5 * period) * sampling_rate)
            end = round((center_time + 0.5 * period) * sampling_rate)
            if end < 1:
                i += 1
                continue
            begin = max(begin, 0)
            end = min(end, len(signal) - 1)
            intervals.append((begin, end, i))
            if end >= len(signal) - 1:
                break
            i += 1

        def compute_correlation(args):
            b, e, idx = args
            corr_res = correlation(waveform[b:e], signal[b:e])
            return idx, b, e, corr_res

        results = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(compute_correlation, interval) for interval in intervals
            ]
            for future in as_completed(futures):
                results.append(future.result())

        # Sort results by period index to keep order
        results.sort(key=lambda x: x[0])

        for idx, b, e, corr_res in results:
            text += (
                f"[green]Correlation for period {idx:3d} with indices {b:5d},{e:5d}: "
                f"[black]{corr_res:.4f} \n"
            )
        return text

    periodicity_detection_method = args.periodicity_detection.lower()

    rpde = periodicity_detection_method == "rpde"
    sf = periodicity_detection_method == "sf"
    corr = periodicity_detection_method == "corr"
    ind = periodicity_detection_method == "ind"

    if args.psd:
        amp = amp * amp / len(amp)
        text = "[green]Spectrum[/]: Power spectrum\n"
    indices = np.arange(1, int(len(amp) / 2) + 1)
    amp_tmp = np.array(2 * amp[indices])
    # norm the data
    amp_tmp = amp_tmp / amp_tmp.sum() if amp_tmp.sum() > 0 else amp_tmp

    text = ""
    if rpde or sf or corr or ind:
        text += f"\n[black]Periodicity Detection[/]"
    if rpde:
        text += f"\n[green]RPDE Score: [black]{compute_rpde(amp_tmp):.4f}[/]\n"
    if sf:
        text += f"\n[green]Spectral Flatness Score: [black]{compute_spectral_flatness(amp_tmp):.4f}[/]\n"
    if corr and len(prediction.dominant_freq) != 0:
        dominant_freq = prediction.dominant_freq[0]
        sampling_freq = prediction.freq
        phi = prediction.phi[0]
        start_time = prediction.t_start
        text += f"\n[green]Correlation Score: [black]{signal_correlation(dominant_freq, sampling_freq, signal, phi, start_time)}[/]\n"
    if ind and len(prediction.dominant_freq) != 0:
        dominant_freq = prediction.dominant_freq[0]
        sampling_freq = prediction.freq
        phi = prediction.phi[0]
        start_time = prediction.t_start
        text += f"\n{ind_period_correlation(dominant_freq, sampling_freq, signal, phi, start_time)}[/]\n"

    return text
