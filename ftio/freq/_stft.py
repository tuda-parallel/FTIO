"""
Short-Time Fourier Transform (STFT) implementation for FTIO.

Author: Ahmad Tarraf
Copyright (c) 2026 TU Darmstadt, Germany
Version: v0.0.8
Date: Feb 2026

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import numpy as np
from scipy.signal import stft


def compute_stft(
    b_sampled: np.ndarray,
    fs: float,
    window: str = "hann",
    nperseg: int = 256,
    noverlap: int = None,
):
    """
    Compute the Short-Time Fourier Transform (STFT) of the signal.

    Parameters:
    - b_sampled: np.ndarray, discretized bandwidth signal.
    - fs: float, sampling frequency.
    - window: str, window function to use (default='hann').
    - nperseg: int, length of each segment (default=256).
    - noverlap: int, number of points to overlap between segments (default=None, which is nperseg // 2).

    Returns:
    - f: np.ndarray, array of sample frequencies.
    - t: np.ndarray, array of segment times.
    - Zxx: np.ndarray, STFT of the signal.
    """
    if nperseg > len(b_sampled):
        nperseg = len(b_sampled)

    f, t, Zxx = stft(b_sampled, fs=fs, window=window, nperseg=nperseg, noverlap=noverlap)
    return f, t, Zxx
