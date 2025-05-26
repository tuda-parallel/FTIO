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
from scipy.stats import spearmanr


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
