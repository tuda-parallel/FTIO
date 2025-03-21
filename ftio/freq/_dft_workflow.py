"""Contains functions that execute workflow using the discrete Fourier Transform.
"""
import time
from argparse import Namespace
import numpy as np
from rich.console import Group
from rich.panel import Panel
from ftio.freq.discretize import sample_data_and_prepare_plots
from ftio.freq._dft import dft, prepare_plot_dft, precision_dft
from ftio.freq.anomaly_detection import outlier_detection
from ftio.freq.helper import MyConsole
from ftio.freq._filter import filter_signal


def ftio_dft(
    args: Namespace,
    bandwidth: np.ndarray,
    time_b: np.ndarray,
    total_bytes: int = 0,
    ranks: int = 1,
    text: str = "",
):
    """
    Performs a Discrete Fourier Transform (DFT) on the sampled bandwidth data, finds the dominant frequency, followed by outlier
    detection to spot the dominant frequency. This function also  prepares the necessary outputs for plotting or reporting.

    Args:
        args (Namespace): The arguments passed to the function, typically containing options for the transformation.
        bandwidth (np.ndarray): Bandwidth values.
        time (np.ndarray): Time points corresponding to the bandwidth values.
        total_bytes (int, optional): Total number of bytes transferred (default = 0).
        ranks (int, optional): The number of ranks (default = 1).
        text (str, optional): Additional text for output. Defaults to "".

    Returns:
        tuple:
            - prediction (dict): Contains prediction results including dominant frequency, confidence, amplitude, etc.
            - df_out (list): A list of DataFrames for plotting.
            - share (dict): Contains shared information, including sampled bandwidth and total bytes.
    """
    #! Default values for variables
    share = {}
    df_out = [[], [], [], []]
    prediction = {
        "source": {args.transformation},
        "dominant_freq": [],
        "conf": [],
        "t_start": 0,
        "t_end": 0,
        "total_bytes": 0,
        "freq": 0,
        "ranks": 0,
    }
    console = MyConsole(verbose=args.verbose)

    #!  Discretize signal: Sample the bandwidth evenly spaced in time
    tik = time.time()
    console.print("[cyan]Executing:[/] Discretization\n")
    b_sampled, args.freq, [df_out[1], df_out[2]] = sample_data_and_prepare_plots(
        args, bandwidth, time_b, ranks
    )
    console.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")


    #! Apply filter if specified
    if args.filter_type:
        b_sampled  = filter_signal(args, b_sampled,)

    #!  Perform DFT
    tik = time.time()
    console.print(
        f"[cyan]Executing:[/] {args.transformation.upper()} + {args.outlier}\n"
    )
    X = dft(b_sampled)
    n = len(X)
    amp = abs(X)
    freq_arr = args.freq * np.arange(0, n) / n
    phi = np.arctan2(X.imag, X.real)
    conf = np.zeros(len(amp))
    # welch(bandwidth,freq)

    #!  Find the dominant frequency
    (
        dominant_index,
        conf[1 : int(n / 2) + 1],
        outlier_text,
    ) = outlier_detection(amp, freq_arr, args)

    #  Ignore DC offset
    conf[0] = np.inf
    if n % 2 == 0:
        conf[int(n / 2) + 1 :] = np.flip(conf[1 : int(n / 2)])
    else:
        conf[int(n / 2) + 1 :] = np.flip(conf[1 : int(n / 2) + 1])

    #!  Assign data
    prediction["dominant_freq"] = freq_arr[dominant_index]
    prediction["conf"] = conf[dominant_index]
    prediction["amp"] = amp[dominant_index]
    prediction["phi"] = phi[dominant_index]
    prediction["t_start"] = time_b[0]
    prediction["t_end"] = time_b[-1]
    prediction["freq"] = args.freq
    prediction["ranks"] = ranks
    prediction["total_bytes"] = total_bytes

    #!  save up to n_freq from the top candidates
    if args.n_freq > 0:
        arr = amp[0 : int(np.ceil(n / 2))]
        top_candidates = np.argsort(-arr)  # from max to min
        n_freq = int(min(len(arr), args.n_freq))
        prediction["top_freq"] = {
            "freq": freq_arr[top_candidates[0:n_freq]],
            "conf": conf[top_candidates[0:n_freq]],
            "amp": amp[top_candidates[0:n_freq]],
            "phi": phi[top_candidates[0:n_freq]],
        }

    if args.autocorrelation:
        share["b_sampled"] = b_sampled
        share["freq"] = args.freq
        share["t_start"] = prediction["t_start"]
        share["t_end"] = prediction["t_end"]
        share["total_bytes"] = prediction["total_bytes"]

    precision_text = ""
    # precision_text = precision_dft(
    #     amp, phi, dominant_index, b_sampled, time_b[0] + np.arange(0, N) * 1/freq, freq_arr, args.engine
    # )
    text = Group(text, outlier_text, precision_text[:-1])

    if any(x in args.engine for x in ["mat", "plot"]):
        df_out[0], df_out[3] = prepare_plot_dft(
            freq_arr, conf, dominant_index, amp, phi, b_sampled, ranks
        )

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
        f"\n[cyan]{args.transformation.upper()} + {args.outlier} finished:[/] {time.time() - tik:.3f} s"
    )
    return prediction, df_out, share
