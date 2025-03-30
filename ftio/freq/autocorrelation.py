"""
This module contains functions to find the period using autocorrelation
and to filter outliers from the detected peaks.
"""

from __future__ import annotations
import time
import numpy as np
from scipy.signal import find_peaks
from rich.panel import Panel
from argparse import Namespace
# from rich.padding import Padding
import ftio.freq.discretize as dis
from ftio.freq.helper import MyConsole
from ftio.plot.plot_autocorrelation import plot_autocorr_results




def find_autocorrelation(args, data: dict, share:dict) -> dict:
    """Finds the period using autocorreleation

    Args:
        args (argparse): command line arguments
        data (dict): sampled data

    Returns:
        dict: predictions containing 4 fields: 
            1. bandwidth (np.array): bandwidth array
            2. time (np.array): time array indicating when bandwidth time points changed
            3. total_bytes (int): total transferred bytes
            4. ranks: number of ranks that did I/O
    """
    prediction = {}
    candidates = np.array([])
    console = MyConsole()
    console.set(args.verbose)
    tik = time.time()
    if args.autocorrelation:
        console.print("[cyan]Executing:[/] Autocorrelation\n")
        prediction = {
        "source":"autocorrelation",
        "dominant_freq": [],
        "conf": [],
        "t_start": 0,
        "t_end": 0,
        "total_bytes": 0,
        }
        # print("    '-> \033[1;32mExecuting Autocorrelation")
        b_sampled = np.array([])
        freq = np.nan
        t_s = np.nan
        t_e = np.nan
        total_bytes = np.nan


        # Take data if already avilable from previous step
        if share:
            b_sampled = share["b_sampled"]
            freq = share["freq"]
            t_s = share["t_start"]
            t_e = share["t_end"]
            total_bytes = share["total_bytes"]
        else:
            total_bytes = 0
            bandwidth = data["bandwidth"] if "bandwidth" in data else np.array([])
            time_b = data["time"] if "time" in data else np.array([])
            t_s = time_b[0]
            t_e = time_b[-1]
            if args.ts:  # shorten data
                time_b = time_b[time_b >= args.ts]
                t_s = time_b[0]
                bandwidth = bandwidth[len(bandwidth) - len(time_b) :]
                total_bytes = np.sum(
                    bandwidth * (np.concatenate([time_b[1:], time_b[-1:]]) - time_b)
                )
                console.print(f"[purple]Start time set to {args.ts:.2f}")
            else:
                console.print(f"[purple]Start time: {time_b[0]:.2f}")

            if args.te:  # shorten data
                time_b = time_b[time_b <= args.te]
                t_s = time_b[-1]
                bandwidth = bandwidth[len(bandwidth) - len(time_b) :]
                total_bytes = np.sum(
                    bandwidth * (np.concatenate([time_b[1:], time_b[-1:]]) - time_b)
                )
                console.print(f"[purple]End time set to {args.te:.2f}")
            else:
                console.print(f"[purple]End time: {time_b[-1]:.2f}")

            # sample the bandwidth bandwidth
            b_sampled, freq = dis.sample_data(bandwidth, time_b, args.freq, args.verbose) 

        res = find_fd_autocorrelation(args, b_sampled, freq)

        #save the results
        prediction["dominant_freq"] = 1/res["periodicity"]  if res["periodicity"] > 0 else np.nan
        prediction["conf"] = res["conf"]
        prediction["t_start"] = t_s
        prediction["t_end"] = t_e
        prediction["total_bytes"] = total_bytes
        prediction["freq"] = freq
        prediction["candidates"] = candidates
        console.print(f"\n[cyan]Autocorrelation finished:[/] {time.time() - tik:.3f} s")
        
    return prediction


def filter_outliers(freq: float, candidates: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, str]:
    """removes outliers using either qunatil method or Z-score

    Args:
        candidates (np.ndarray): peaks
        weights (np.ndarray): weights of the peaks

    Returns:
        np.ndarray: outliers
        str: string text
    """
    text = ""
    outliers = np.array([])
    # remove outliers:
    if len(candidates) > 0 and any(candidates > 0):
        ind = np.where(candidates > 1/freq)
        candidates = candidates[ind] # remove everythin above 10 Hz
        if len(weights > 0):
            weights = weights[ind]
        method = "z"
        # With quantil and weights
        if "q" in method:
            text += f"Filtering method: [purple]quantil[/]\n"
            # candidates = candidates*weights/sum(weights)
            q1 = np.percentile(candidates, 25)
            q3 = np.percentile(candidates, 75)
            iqr = q3 - q1
            threshold = 1.5 * iqr
            outliers = np.where(
                (candidates < q1 - threshold) | (candidates > q3 + threshold)
            )
        elif "z" in method:
            text += "Filtering method: [purple]Z-score with weighteed mean[/]\n"
            # With Zscore:
            mean = np.average(candidates, weights=weights) if len(weights) > 0 else 0
            # std = np.std(candidates)
            std =  np.sqrt(np.abs(np.average((candidates-mean)**2, weights=weights))) if len(weights) > 0 else 0
            text += f"Wighted mean is [purple]{mean:.3f}[/] and weighted std. is [purple]{std:.3f}[/]\n"
            z_score = np.abs((candidates - mean) / std) if std != 0  else np.array([])
            outliers = np.where(z_score > 1)
            text += f"Z-score is [purple]{print_array(z_score)}[/]\n"
        
        text += (
            f"[purple]{len(candidates)}[/] period candidates found:\n"
            f"[purple]{print_array(candidates)}[/]\n\n"
            f"{len(candidates[outliers])} outliers found:\n[purple]{print_array(candidates[outliers])}[/]\n\n"
        )
    else:
        text += "[purple]Empty[/]\n"

    return outliers, text


def find_fd_autocorrelation(args: Namespace, b_sampled: np.ndarray, freq: float) -> dict:
    """
    Computes the autocorrelation of a sampled signal, detects peaks, and calculates periodicity and confidence
    based on the detected periods.

    Args:
        args (Namespace): Command line arguments.
        b_sampled (np.ndarray): The sampled input signal.
        freq (float): The frequency at which the signal is sampled.

    Returns:
        dict: A dictionary containing the autocorrelation, peak locations, weights, 
                calculated periodicity, and confidence level.
    """
    # Compute autocorrelation of the sampled signal
    acorr = autocorrelation(b_sampled)

    # Finding peak locations and calculating the average time differences between them
    peaks, prop = find_peaks(acorr, height=0.15)
    candidates = np.diff(peaks) / freq
    weights = np.diff(prop['peak_heights'])

    # Removing outliers
    outliers, text = filter_outliers(freq, candidates, weights)
    if outliers:
        candidates = np.delete(candidates, outliers)
        weights = np.delete(weights, outliers)
        
    # Calculating period and its statistics
    if candidates.size > 0:
        mean = np.average(candidates, weights=weights)
        std = np.sqrt(np.abs(np.average((candidates - mean) ** 2, weights=weights)))
        tmp = [f"{1/i:.4f}" for i in candidates]  # Formatting frequencies
        periodicity = mean
        coef_var = np.abs(std / mean)
        conf = 1 - coef_var
    else:
        mean = np.nan
        std = np.nan
        tmp = np.nan
        periodicity = np.nan
        conf = np.nan

    # Building output text
    text += (
        f"Found periods are [purple]{candidates}[/]\n"
        f"Matching frequencies are [purple]{tmp}[/]\n"
        f"Average period is [purple]{periodicity:.2f} [/]sec\n"
        f"Average frequency is [purple]{1/periodicity if periodicity > 0 else np.nan:.4f} [/]Hz\n"
        f"Confidence is [purple]{conf * 100:.2f} [/]%\n"
    )
    console = MyConsole()
    console.set(args.verbose)
    console.print(Panel.fit(text[:-1], style="white", border_style="purple", title="Autocorrelation", title_align="left"))

    # plot
    plot_autocorr_results(args, acorr, peaks, outliers, len(candidates) > 0)

    return {"autocorrelation": acorr, "candidates": candidates, "peaks": peaks, "outliers": outliers, "weights": weights, "periodicity": periodicity, "conf": conf}


def autocorrelation(arr: np.ndarray) -> np.ndarray:
    """
    Computes the autocorrelation of a given array.

    Args:
        arr (np.ndarray): Input array for which to compute the autocorrelation.

    Returns:
        np.ndarray: Autocorrelation values.
    """
    # Scipy autocorrelation
    # lags = range(int(freq*len(arr)))
    # acorr = sm.tsa.acf(arr, nlags = len(lags)-1)
    #! numpy autocorrelation
    # # Mean
    mean = np.mean(arr)
    # Variance
    var = np.var(arr)
    # Normalized data
    ndata = arr - mean
    # Calculate autocorrelation:
    acorr = np.correlate(ndata, ndata, "full")[len(ndata) - 1 :]
    acorr = acorr / var / len(ndata)

    return acorr


def print_array(array:np.ndarray) -> str:
    out = ""
    if len(array) == 0:
        out =" "
    for i in array:
        out += f" {i:.2f}"

    return "["+out[1:]+"]"
