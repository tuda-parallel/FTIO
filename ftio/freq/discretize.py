"""Module contains function functions to discretize the data."""

from __future__ import annotations

from argparse import Namespace

import numpy as np
import pandas as pd
from numba import jit
from rich.panel import Panel

from ftio.freq.helper import MyConsole


def sample_data(
    b: np.ndarray, t: np.ndarray, freq: float = -1, verbose: bool = False
) -> tuple[np.ndarray, float]:
    """
    Samples the data at equal time steps  according to the specified frequency.

    Args:
        b (np.ndarray): Bandwidth values.
        t (np.ndarray): Time points corresponding to the bandwidth values.
        freq (float, optional): Sampling frequency. Defaults to -1, which triggers automatic calculation of the optimal sampling frequency.
        verbose (bool, optional): Flag to indicated if information about the sampling process, including the time window, frequency step, and abstraction error is
        printed

    Returns:
        tuple: A tuple containing:
            - b_sampled (np.ndarray): Uniform sampled bandwidth values.
            - freq (float): The frequency used for sampling (calculated if freq was -1).

    Raises:
        RuntimeError: If no data is found in the sampled bandwidth.
    """
    text = ""
    
    # Check for empty array first
    if len(t) == 0:
        return np.empty(0), 0
        
    text += f"Time window: {t[-1]-t[0]:.2f} s\n"
    text += f"Frequency step: {1/(t[-1]-t[0]) if (t[-1]-t[0]) != 0 else 0:.3e} Hz\n"

    # ? calculate recommended frequency:
    if freq == -1:
        t_rec = find_lowest_time_change(t)
        freq = 2 / t_rec
        text += f"Recommended sampling frequency: {freq:.3e} Hz\n"
    elif freq == -2:
        N = 10000
        freq = N / np.floor((t[-1] - t[0])) if t[-1] != t[0] else 1000
    else:
        text += f"Sampling frequency:  {freq:.3e} Hz\n"
    N = int(np.floor((t[-1] - t[0]) * freq))
    text += f"Expected samples: {N}\n"
    # print("    '-> \033[1;Start time: %f s \033[1;0m"%t[0])

    # ? sample the data with the recommended frequency
    # t_sampled = np.zeros(N) #t[0]+np.arange(N)*1/freq
    b_sampled = np.zeros(N)
    n = len(t)
    counter = 0
    n_old = 0
    t_step = t[0]
    # error   = 0
    # errorStep   = 0
    for _ in range(0, N):
        for i in range(n_old, n):
            if (t_step >= t[i]) and (t_step < t[i + 1]) or i == n - 1:
                n_old = i  # no need to iterate over entire array
                b_sampled[counter] = b[i]
                counter = counter + 1
                break
        t_step = t_step + 1 / freq

    #! Abstraction error
    v_a = np.sum(np.abs(b_sampled * np.repeat(1 / freq, len(b_sampled))))
    v_0 = np.sum(b * (np.concatenate([t[1:], t[-1:]]) - t))
    # E = (abs(error))/(V0) if V0 > 0 else 0
    error = (abs(v_a - v_0)) / v_0 if v_0 > 0 else 0
    text += f"Abstraction error: {error:.5f}\n"

    if len(b_sampled) == 0:
        raise RuntimeError(
            "No data in sampled bandwidth.\n Try increasing the sampling frequency"
        )

    console = MyConsole(verbose)
    console.print(
        Panel.fit(
            text[:-1],
            style="white",
            border_style="yellow",
            title="Discretization",
            title_align="left",
        )
    )

    return b_sampled, freq


def sample_data_same_size(
    b: np.ndarray, t: np.ndarray, freq=-1, n_bins=-1
) -> tuple[np.ndarray, np.ndarray]:
    """
    Discretize the data according to the specified frequency, ensuring the sampled data has the same
    number of bins as specified.

    This function samples the bandwidth data at the given frequency and returns the sampled
    data along with the corresponding time points, ensuring the number of bins is consistent with the provided `n_bins` value.

    Args:
        b (np.ndarray): Bandwidth values.
        t (np.ndarray): Time points corresponding to the bandwidth values.
        freq (float, optional): Sampling frequency. Defaults to -1, which triggers automatic calculation of the optimal sampling frequency.
        n_bins (int, optional): The desired number of bins for the sampled data.


    Returns:
        tuple: A tuple containing:
            - b_sampled (np.ndarray): Sampled bandwidth values.
            - t_sampled (np.ndarray): Time points corresponding to the sampled data.
    """
    print(f"    '-> \033[1;34mBins: {n_bins}  \033[1;0m")
    b_sampled = np.zeros(n_bins)
    n_old = 0
    counter = 0
    t_step = 0
    n = len(b)
    for k in range(0, n_bins):
        if (t_step < t[0]) or (t_step > t[-1]):
            counter = counter + 1
        else:
            for i in range(n_old, n):
                if (t_step >= t[i]) and (t_step < t[i + 1]) or i == n - 1:
                    n_old = i  # no need to itterate over entire array
                    b_sampled[counter] = b[i]
                    counter = counter + 1
                    break
        t_step = t_step + 1 / freq

    t = np.arange(0, n_bins) * 1 / freq
    return b_sampled, t


@jit(nopython=True, cache=True)
def find_lowest_time_change(t: np.ndarray) -> float:
    """finds the lowest time change

    Args:
        t (np.ndarray): array of time stamps

    Returns:
        float: smallest time change
    """
    t_rec = np.inf
    for i in range(0, len(t) - 1):
        if (
            t_rec > (t[i + 1] - t[i])
            and (t[i + 1] - t[i]) != 0
            # and (t[i + 1] - t[i]) >= 0.001
        ):
            t_rec = t[i + 1] - t[i]

    if t_rec <= 0.001:
        t_rec = 0.001

    return t_rec


def sample_data_and_prepare_plots(
    args: Namespace, bandwidth: np.ndarray, time_b: np.ndarray, ranks: int
) -> tuple[np.ndarray, float, list[list[pd.DataFrame]]]:
    """
    Samples the data and prepares plots if required.

    Args:
        args (Namespace): Arguments containing frequency and engine options.
        bandwidth (np.ndarray): The bandwidth data.
        time_b (np.ndarray): The time data.
        ranks (int): The number of ranks.

    Returns:
        tuple: A tuple containing:
            - The sampled bandwidth data (b_sampled),
            - The frequency (freq),
            - A list of DataFrames (df_sample) for plotting.
    """
    # sample the data
    b_sampled, freq = sample_data(bandwidth, time_b, args.freq, args.verbose)

    # prepare data for plotting
    figures_data = AnalysisFigures()
    if any(x in args.engine for x in ["mat", "plot"]):
        figures_data = prepare_plot_sample(bandwidth, time_b, freq, len(b_sampled), ranks)

    return b_sampled, freq, figures_data
