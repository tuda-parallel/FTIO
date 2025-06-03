"""
This file provides functions to compute similarities between time series

Author: Ahmad Tarraf
Copyright (c) 2025 TU Darmstadt, Germany
Date: Mai 26 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import numpy as np
from matplotlib import pyplot as plt
from scipy.stats import spearmanr

from ftio.freq.helper import MyConsole
from ftio.plot.units import set_unit


def correlation(x, y, method="pearson"):
    """
    Compute global correlation between two signals.

    Parameters:
        x, y   : Input 1D signals (must be same length)
        method : 'pearson' or 'spearman'

    Returns:
        r      : Correlation coefficient
    """
    if len(x) != len(y):
        raise ValueError("Signals must have the same length.")

    if method == "pearson":
        if np.std(x) == 0 or np.std(y) == 0:
            return 0
        return np.corrcoef(x, y)[0, 1]

    elif method == "spearman":
        rho, _ = spearmanr(x, y)
        return rho if not np.isnan(rho) else 0

    else:
        raise ValueError("Unsupported method: choose 'pearson' or 'spearman'")


def sliding_correlation(x, y, window_size, method="pearson"):
    """
    Compute local correlation (Pearson or Spearman) in a sliding window.

    Parameters:
        x, y        : Input 1D signals (must be same length)
        window_size : Size of window in samples
        method      : 'pearson' or 'spearman'

    Returns:
        corrs       : Array of local correlation values
    """
    n = len(x)
    w = window_size
    corrs = np.zeros(n - w + 1)

    for i in range(len(corrs)):
        x_win = x[i : i + w]
        y_win = y[i : i + w]
        corrs[i] = correlation(x_win, y_win, method)

    return corrs


def plot_correlation(
    t, signal_1, signal_2, corrs, window_duration=None, name=["Cosine", "Logical"]
):
    """
    Plot input signals, sliding correlation, and their product.

    Parameters:
        t               : Time vector (1D array)
        signal_1        : First input signal (1D array)
        signal_2        : Second input signal (1D array)
        corrs           : Sliding correlation values (1D array)
        window_duration : Optional duration of the correlation window (float)
        name            : List of two string indicating the label on the plot
    """
    # Ensure aligned time vector for correlation
    min_len = min(len(signal_1), len(signal_2), len(corrs))
    signal_1 = signal_1[:min_len]
    signal_2 = signal_2[:min_len]
    t_corr = t[:min_len]
    corrs = corrs[:min_len]
    masked_corr = signal_1 * signal_2
    # plt.figure(figsize=(10, 8))
    # plt.subplot(3, 1, 1)
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)

    # Plot signals
    unit, order = set_unit(signal_2)
    plt.plot(t_corr, order * signal_1, label=f"{name[0]}")
    plt.plot(t_corr, order * signal_2, label=f"{name[1]}", linestyle="--")
    plt.title("Signals from DWT and DFT", fontsize=17)
    plt.xlim(t_corr[0], t_corr[-1])
    plt.legend(loc="upper right")
    plt.ylabel(f"Bandwidth ({unit})", fontsize=17)
    plt.xlabel("Time (s)", fontsize=17)
    plt.grid(True)

    # Plot correlation
    # plt.subplot(3, 1, 2)
    plt.subplot(2, 1, 2)
    plt.plot(t_corr, corrs, color="purple")
    plt.axhline(0, color="gray", linestyle="--")
    title = "Sliding Window Correlation"
    if window_duration:
        title += f" (Window = {window_duration:.1f} s)"
    plt.title(title, fontsize=17)
    plt.xlim(t_corr[0], t_corr[-1])
    plt.ylabel("Correlation", fontsize=17)
    plt.xlabel("Time (s)", fontsize=17)
    plt.grid(True)

    # Plot masked cosine
    # plt.subplot(3, 1, 3)
    # plt.plot(t_corr, masked_corr, label=f"Masked {name[0]}", color="teal")
    # # plt.title(f"{name[0]} masked by {name[1]} Signal")
    # plt.title(f"Cosine wave masked approximation coefficients", fontsize=15)
    # plt.xlabel("Time (s)", fontsize=17)
    # plt.xlim(t_corr[0], t_corr[-1])
    # plt.grid(True)

    plt.tight_layout()
    plt.show()


def extract_correlation_ranges(
    t: np.ndarray,
    corrs: np.ndarray,
    threshold_low: float = 0.12,
    threshold_high: float = 1.0,
    min_duration: float = 0.0,
    verbose: bool = False,
) -> list[tuple[float, float]]:
    """
    Extract continuous time ranges where correlation is between threshold_low and threshold_high,
    and discard segments shorter than min_duration.

    Parameters:
        t              : Time vector (1D array)
        corrs          : Correlation values (same length as t)
        threshold_low  : Lower threshold (inclusive)
        threshold_high : Upper threshold (inclusive)
        min_duration   : Minimum duration of a valid segment (in seconds)
        verbose        : If set, prints the result on the console

    Returns:
        List of (start_time, end_time) tuples
    """
    assert len(t) == len(corrs), "Time and correlation arrays must be the same length"
    mask = (corrs >= threshold_low) & (corrs <= threshold_high)

    # Find rising and falling edges of the mask
    edges = np.diff(mask.astype(int))
    start_indices = np.where(edges == 1)[0] + 1
    end_indices = np.where(edges == -1)[0] + 1

    # Handle edge cases where mask starts or ends True
    if mask[0]:
        start_indices = np.r_[0, start_indices]
    if mask[-1]:
        end_indices = np.r_[end_indices, len(mask)]

    # Create ranges and filter by duration
    ranges = []
    for start, end in zip(start_indices, end_indices):
        t_start, t_end = t[start], t[end - 1]
        if (t_end - t_start) >= min_duration:
            ranges.append((t_start, t_end))

    # Step 2: Merge nearby ranges
    if ranges:
        merged_ranges = [ranges[0]]
        for curr_start, curr_end in ranges[1:]:
            prev_start, prev_end = merged_ranges[-1]
            if curr_start - prev_end < min_duration:
                # Merge with previous
                merged_ranges[-1] = (prev_start, curr_end)
            else:
                merged_ranges.append((curr_start, curr_end))
    else:
        merged_ranges = []

    if merged_ranges:
        console = MyConsole(verbose)
        for start, end in merged_ranges:
            console.info(
                f"Correlation between {threshold_low} and {threshold_high} from {start:.2f}s to {end:.2f}s"
            )

    return merged_ranges
