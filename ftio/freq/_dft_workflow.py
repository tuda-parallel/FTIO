"""Contains functions that execute workflow using the discrete Fourier Transform.
"""
import time
from argparse import Namespace
import numpy as np
from rich.console import Group
from rich.panel import Panel

from ftio.freq._fourier_fit import fourier_fit
from ftio.freq.discretize import sample_data
from ftio.freq._dft import dft, prepare_plot_dft, precision_dft
from ftio.freq.anomaly_detection import outlier_detection
from ftio.freq.helper import MyConsole
from ftio.freq._filter import filter_signal
from ftio.freq._share_signal_data import SharedSignalData
from ftio.freq.prediction import Prediction
from ftio.freq._analysis_figures import AnalysisFigures
from ftio.plot.plot_dft import plot_dft


def ftio_dft(
    args: Namespace,
    bandwidth: np.ndarray,
    time_stamps: np.ndarray,
    total_bytes: int = 0,
    ranks: int = 1,
    text: str = "",
)-> tuple[Prediction,AnalysisFigures,SharedSignalData]:
    """
    Performs a Discrete Fourier Transform (DFT) on the sampled bandwidth data, finds the dominant frequency, followed by outlier
    detection to spot the dominant frequency. This function also  prepares the necessary outputs for plotting or reporting.

    Args:
        args (Namespace): The arguments passed to the function, typically containing options for the transformation.
        bandwidth (np.ndarray): Bandwidth values.
        time_stamps (np.ndarray): Time points corresponding to the bandwidth values.
        total_bytes (int, optional): Total number of bytes transferred (default = 0).
        ranks (int, optional): The number of ranks (default = 1).
        text (str, optional): Additional text for output. Defaults to "".

    Returns:
        tuple:
            - prediction (Prediction): Contains prediction results including dominant frequency, confidence, amplitude, etc.
            - analysis_figures (AnalysisFigures): Data and plot figures.
            - share (SharedSignalData): Contains shared information, including sampled bandwidth and total bytes.
    """
    #! Default values for variables
    share = SharedSignalData()
    prediction = Prediction(args.transformation)
    console = MyConsole(verbose=args.verbose)

    #!  Sample the bandwidth evenly spaced in time
    tik = time.time()
    console.print("[cyan]Executing:[/] Discretization\n")
    b_sampled, args.freq =  sample_data(bandwidth, time_stamps, args.freq, args.verbose)
    console.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")

    #! Apply filter if specified
    if args.filter_type:
        b_sampled  = filter_signal(args, b_sampled)

    #!  Perform DFT
    tik = time.time()
    console.print(
        f"[cyan]Executing:[/] {args.transformation.upper()} + {args.outlier}\n"
    )
    n = len(b_sampled)
    frequencies = args.freq * np.arange(0, n) / n
    X = dft(b_sampled)
    X = X * np.exp(-2j * np.pi * frequencies * time_stamps[0]) # Correct phase offset due to start time t0
    amp = abs(X)
    phi = np.arctan2(X.imag, X.real)
    conf = np.zeros(len(amp))
    # welch(bandwidth,freq)

    #!  Find the dominant frequency
    (
        dominant_index,
        conf[1 : int(n / 2) + 1],
        outlier_text
    ) = outlier_detection(amp, frequencies, args)

    #  Ignore DC offset
    conf[0] = np.inf
    if n % 2 == 0:
        conf[int(n / 2) + 1 :] = np.flip(conf[1 : int(n / 2)])
    else:
        conf[int(n / 2) + 1 :] = np.flip(conf[1 : int(n / 2) + 1])

    #! Assign data
    prediction.dominant_freq = frequencies[dominant_index]
    prediction.conf = conf[dominant_index]
    prediction.amp = amp[dominant_index]
    prediction.phi = phi[dominant_index]
    prediction.t_start = time_stamps[0]
    prediction.t_end = time_stamps[-1]
    prediction.freq = args.freq
    prediction.ranks = ranks
    prediction.total_bytes = total_bytes
    prediction.n_samples = n

    #! Save up to n_freq from the top candidates
    if args.n_freq > 0:
        arr = amp[0 : int(np.ceil(n / 2))]
        top_candidates = np.argsort(-arr)  # from max to min
        n_freq = int(min(len(arr), args.n_freq))
        prediction.top_freqs = {
            "freq": frequencies[top_candidates[0:n_freq]],
            "conf": conf[top_candidates[0:n_freq]],
            "amp": amp[top_candidates[0:n_freq]],
            "phi": phi[top_candidates[0:n_freq]],
        }

    t_sampled = time_stamps[0] + np.arange(0, n) * 1 / args.freq

    #! Plot
    if any(x in args.engine for x in ["mat", "plot"]):
        console.print(f"Generating {args.transformation.upper()} Plot\n")
        analysis_figures = AnalysisFigures(args, bandwidth, time_stamps, b_sampled, t_sampled,
                                           frequencies, amp, phi, conf, ranks)
        if not args.autocorrelation:
            plot_dft(args, prediction, analysis_figures)
        console.print(f" --- Done --- \n")
    else:
        analysis_figures = AnalysisFigures()

    #! Fourier fit if set
    if args.fourier_fit:
        fourier_fit(args, prediction, analysis_figures, b_sampled, t_sampled)


    if args.autocorrelation:
        share.set_data_from_predicition(b_sampled,prediction)

    precision_text = ""
    # precision_text = precision_dft(amp, phi, dominant_index, b_sampled, t_sampled, frequencies, args.engine)
    text = Group(text, outlier_text, precision_text[:-1])



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
    return prediction, analysis_figures, share
