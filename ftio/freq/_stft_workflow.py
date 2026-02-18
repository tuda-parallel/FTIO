"""
STFT workflow for FTIO. This module implements the
Short-Time Fourier Transform (STFT) processing pipeline used
by FTIO. It handles resampling of bandwidth time-series data, executes
the STFT analysis, and prepares prediction and analysis outputs in a
format compatible with the FTIO framework.

Author: Ahmad Tarraf
Copyright (c) 2026 TU Darmstadt, Germany
Version: v0.0.8
Date: Feb 2026

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import copy
import time
from argparse import Namespace

import numpy as np
from rich.console import Group
from rich.panel import Panel

from ftio.analysis.anomaly_detection import outlier_detection
from ftio.analysis.periodicity_analysis import new_periodicity_scores
from ftio.freq._analysis_figures import AnalysisFigures
from ftio.freq._stft import compute_stft
from ftio.freq.discretize import sample_data
from ftio.freq.helper import MyConsole
from ftio.freq.prediction import Prediction
from ftio.plot.plot_stft import plot_stft
from ftio.processing.print_output import display_prediction


def ftio_stft(
    args: Namespace,
    bandwidth: np.ndarray,
    time_stamps: np.ndarray,
    total_bytes: int = 0,
    ranks: int = 1,
    text: str = "",
) -> tuple[Prediction, AnalysisFigures]:
    """
    Performs a Short-Time Fourier Transform (STFT) on the sampled bandwidth data.

    Args:
        args (Namespace): The arguments passed to the function.
        bandwidth (np.ndarray): Bandwidth values.
        time_stamps (np.ndarray): Time points corresponding to the bandwidth values.
        total_bytes (int, optional): Total number of bytes transferred.
        ranks (int, optional): The number of ranks.
        text (str, optional): Additional text for output.

    Returns:
        tuple: (prediction, analysis_figures)
    """
    prediction = Prediction(args.transformation)
    analysis_figures = AnalysisFigures(args)
    console = MyConsole(verbose=args.verbose)

    #! Sample the bandwidth evenly spaced in time
    tik = time.time()
    console.print("[cyan]Executing:[/] Discretization\n")
    b_sampled, args.freq = sample_data(bandwidth, time_stamps, args)
    console.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")

    #! Perform STFT
    tik = time.time()
    # Use default or reasonable parameters for STFT
    fs = args.freq

    # Determine window length (nperseg) in samples.
    # A larger nperseg increases frequency resolution (fs/nperseg)
    # but decreases time resolution (nperseg/fs).
    if args.stft_window > 0:
        nperseg = args.stft_window
    else:
        # Automatically determine window size:
        # We aim for ~5 periods of the dominant frequency found via DFT
        # to get a balanced time-frequency representation.
        from ftio.freq._dft_workflow import ftio_dft

        temp_args = copy.deepcopy(args)
        temp_args.engine = "no"
        temp_args.verbose = False
        temp_args.stft_window = 0  # Avoid recursion
        temp_args.periodicity_detection = None  # Silence print in dft
        temp_prediction, _ = ftio_dft(
            temp_args, bandwidth, time_stamps, total_bytes, ranks
        )

        dominant_freq = temp_prediction.get_dominant_freq()
        if not np.isnan(dominant_freq) and dominant_freq > 0:
            # Calculate samples needed for 5 periods: 5 * (fs / freq)
            nperseg = int(5 * fs / dominant_freq)
            # If window is too small (e.g., less than 10th of the trace),
            # fallback to a reasonable default to avoid over-segmentation.
            if nperseg < len(b_sampled) // 10:
                nperseg = min(len(b_sampled), 256)
        else:
            nperseg = min(len(b_sampled), 256)

    # Ensure nperseg is valid (at least 2 samples, no more than total length)
    nperseg = min(max(nperseg, 2), len(b_sampled))

    console.print(
        f"[cyan]Executing:[/] {args.transformation.upper()} (window size: {nperseg})\n"
    )

    f, t_stft, Zxx = compute_stft(b_sampled, fs, nperseg=nperseg)

    # Calculate magnitude
    amp_stft = np.abs(Zxx)
    # To find a dominant frequency for the Prediction object, we can use the mean amplitude over time
    amp_mean = np.mean(amp_stft, axis=1)

    #! Find the dominant frequency using mean amplitude (global summary)
    dominant_index_global, conf_global, outlier_text = outlier_detection(
        amp_mean, f, args
    )

    #! Find the dominant frequency in each time window using outlier detection
    dominant_freqs = []
    conf_vals = []
    amplitudes = []
    phases = []
    window_predictions = []

    # Disable plotting for per-window outlier detection to avoid overhead/multiple plots
    original_engine = args.engine
    args.engine = "no"

    # Calculate window width
    dt = t_stft[1] - t_stft[0] if len(t_stft) > 1 else (time_stamps[-1] - time_stamps[0])

    for i in range(amp_stft.shape[1]):
        # Perform outlier detection on each window
        # We suppress the output text as we don't need it per window
        d_idx, d_conf, _ = outlier_detection(amp_stft[:, i], f, args)

        win_pred = Prediction(f"STFT_WINDOW_{i}")
        win_pred.t_start = t_stft[i] - dt / 2
        win_pred.t_end = t_stft[i] + dt / 2
        win_pred.freq = args.freq
        win_pred.ranks = ranks
        win_pred.total_bytes = total_bytes  # Approximate
        win_pred.n_samples = nperseg

        if d_idx:
            # Pick the one with the highest amplitude among the detected outliers
            best_idx = d_idx[np.argmax(amp_stft[d_idx, i])]
            dominant_freqs.append(f[best_idx])
            # d_conf is usually indexed from 0 to n/2-1, corresponding to f[1:n/2+1]
            try:
                c = d_conf[best_idx - 1]
            except IndexError:
                c = 0
            conf_vals.append(c)
            amplitudes.append(amp_stft[best_idx, i])
            phases.append(np.angle(Zxx[best_idx, i]))

            win_pred.dominant_freq = np.array([f[best_idx]])
            win_pred.conf = np.array([c])
            win_pred.amp = np.array([amp_stft[best_idx, i]])
            win_pred.phi = np.array([np.angle(Zxx[best_idx, i])])
        else:
            # Fallback to the maximum amplitude if no outlier is found
            best_idx = np.argmax(amp_stft[:, i])
            dominant_freqs.append(f[best_idx])
            conf_vals.append(0)  # Low confidence
            amplitudes.append(amp_stft[best_idx, i])
            phases.append(np.angle(Zxx[best_idx, i]))

            win_pred.dominant_freq = np.array([f[best_idx]])
            win_pred.conf = np.array([0])
            win_pred.amp = np.array([amp_stft[best_idx, i]])
            win_pred.phi = np.array([np.angle(Zxx[best_idx, i])])

        window_predictions.append(win_pred)

    # Restore original engine
    args.engine = original_engine

    # Display results for each window if verbose or if explicitly desired
    # Similar to wavelet_disc workflow

    for j, win_pred in enumerate(window_predictions):
        console.info(
            f"\n[bold cyan]--- Window {j} ([{win_pred.t_start:.2f}, {win_pred.t_end:.2f}] s) ---[/]"
        )
        display_prediction(args, win_pred)

    #! Assign data to prediction (global summary)
    prediction.dominant_freq = np.array(dominant_freqs)
    prediction.conf = np.array(conf_vals)
    prediction.amp = np.array(amplitudes)
    prediction.phi = np.array(phases)
    prediction.t_start = time_stamps[0]
    prediction.t_end = time_stamps[-1]
    prediction.freq = args.freq
    prediction.ranks = ranks
    prediction.total_bytes = total_bytes
    prediction.n_samples = len(b_sampled)

    # Save up to n_freq from the top candidates based on amp_mean
    if args.n_freq > 0:
        n = len(amp_mean)
        arr = amp_mean[0 : int(np.ceil(n / 2))]
        top_candidates = np.argsort(-arr)  # from max to min
        n_freq = int(min(len(arr), args.n_freq))

        # Reconstruct conf for top candidates if not all were caught by global outlier detection
        # conf_global is size n/2, so we pad it to size n
        full_conf = np.zeros(n)
        full_conf[1 : len(conf_global) + 1] = conf_global

        # Approximate phase for global frequencies from the mean complex spectrum
        Zxx_mean = np.mean(Zxx, axis=1)
        phi_global = np.angle(Zxx_mean)

        prediction.top_freqs = {
            "freq": f[top_candidates[0:n_freq]],
            "conf": full_conf[top_candidates[0:n_freq]],
            "periodicity": np.zeros(n_freq),
            "amp": amp_mean[top_candidates[0:n_freq]],
            "phi": phi_global[top_candidates[0:n_freq]],
        }

    periodicity_score = new_periodicity_scores(amp_mean, b_sampled, prediction, args)

    #! Prepare for plotting
    if any(x in args.engine for x in ["mat", "plot"]):
        console.print(f"Generating {args.transformation.upper()} Plot\n")
        # STFT Spectrogram and Reconstruction Plots
        figs = plot_stft(args, prediction, b_sampled, fs, stft_data=(f, t_stft, Zxx))
        if figs:
            analysis_figures.add_figure(figs, "stft")

        # Reuse AnalysisFigures for frequency spectrum plot
        t_sampled = time_stamps[0] + np.arange(len(b_sampled)) / args.freq
        analysis_figures += AnalysisFigures(
            args,
            bandwidth,
            time_stamps,
            b_sampled,
            t_sampled,
            f,
            amp_mean,
            None,
            conf_global,
            ranks,
        )

        # Display figures if needed
        analysis_figures.show()
        console.print(" --- Done --- \n")

    text = Group(text, outlier_text, periodicity_score)

    console.print(
        Panel.fit(
            text,
            style="white",
            border_style="cyan",
            title=args.transformation.upper(),
            title_align="left",
        )
    )
    console.print(
        f"\n[cyan]{args.transformation.upper()} finished:[/] {time.time() - tik:.3f} s"
    )

    return prediction, analysis_figures
