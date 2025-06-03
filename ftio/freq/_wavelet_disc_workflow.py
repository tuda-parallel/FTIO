"""Contains functions that execute workflow using the continuous Wavelet Transform."""

import copy
import time
from argparse import Namespace
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from ftio.analysis._logicize import logicize
from ftio.freq._analysis_figures import AnalysisFigures
from ftio.freq._dft_workflow import ftio_dft
from ftio.freq._dft_x_dwt import analyze_correlation
from ftio.freq._share_signal_data import SharedSignalData
from ftio.freq._wavelet import wavelet_disc
from ftio.freq._wavelet_helpers import (
    decomposition_level,
    upsample_coefficients,
    wavelet_freq_bands,
)
from ftio.freq.autocorrelation import find_fd_autocorrelation
from ftio.freq.discretize import sample_data
from ftio.freq.helper import MyConsole
from ftio.plot.freq_plot import convert_and_plot
from ftio.plot.plot_wavelet_disc import (
    plot_coeffs_reconst_signal,
    plot_wavelet_disc_spectrum,
)
from ftio.processing.print_output import display_prediction

# from ftio.prediction.helper import[] get_dominant_and_conf


def ftio_wavelet_disc(
    args: Namespace,
    bandwidth: np.ndarray,
    time_stamps: np.ndarray,
    ranks: int = 0,
    total_bytes: int = 0,
):
    """
    Executes discrete wavelet transformation on the provided bandwidth data.

    Args:
        args: The Namespace object containing configuration options.
        bandwidth (np.ndarray): The bandwidth data to process.
        time_stamps (np.ndarray): The corresponding time points for the bandwidth data.
        ranks (int): The rank value (default is 0).
        total_bytes (int): total transferred bytes (default is 0).
    """
    # Default values for variables
    share = SharedSignalData()
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

    # ! Sample the bandwidth evenly spaced in time
    tik = time.time()
    console.print("[cyan]Executing:[/] Discretization\n")
    b_sampled, args.freq = sample_data(bandwidth, time_stamps, args.freq, args.verbose)
    console.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")

    # b_sampled = logicize(b_sampled)

    tik = time.time()
    console.print(f"[cyan]Executing:[/] {args.transformation.upper()} + {args.outlier}\n")

    # ! Find the level for the discrete wavelet
    # https://edisciplinas.usp.br/pluginfile.php/4452162/mod_resource/content/1/V1
    # -Parte%20de%20Slides%20de%20p%C3%B3sgrad%20PSI5880_PDF4%20em%20Wavelets%20
    # -%202010%20-%20Rede_AIASYB2.pdf
    # https://www.youtube.com/watch?v=hAQQwvKsWCY&ab_channel=NathanKutz
    console.print("[green]Performing discrete wavelet decomposition[/]")
    # Max level or use DFT
    method = "dft"
    if args.level == 0:
        if method == "dft":
            args.transformation = "dft"
            prediction, _, _ = ftio_dft(args, bandwidth, time_stamps, total_bytes, ranks)
            if len(prediction.dominant_freq) > 0:
                args.level = int(1 / (5 * prediction.get_dominant_freq()))
                console.print(f"[green]Decomposition level adjusted to {args.level}[/]")
                args.transformation = "wave_disc"
            else:
                args.level = decomposition_level(args, len(b_sampled))
        else:
            args.level = decomposition_level(args, len(b_sampled))

    # ! calculate the coefficients using the discrete wavelet
    # args.wavelet = "db8"
    # coefficients ->  [cA_n, cD_n, cD_n-1, …, cD2, cD1]
    coefficients = wavelet_disc(b_sampled, args.wavelet, args.level)
    # compute the frequency ranges
    freq_ranges = wavelet_freq_bands(args.freq, args.level)
    # Upsample coefficients for equal length
    t_sampled = time_stamps[0] + np.arange(0, len(b_sampled)) * 1 / args.freq
    coefficients_upsampled = upsample_coefficients(
        coefficients, args.wavelet, len(b_sampled)
    )
    # plot functions
    if any(x in args.engine for x in ["mat", "plot"]):
        console.print(f"Generating {args.transformation.upper()} Plot\n")
        analysis_figures_wavelet = AnalysisFigures(
            args, coefficients=coefficients_upsampled
        )
        f1 = plot_coeffs_reconst_signal(
            args,
            time_stamps,
            bandwidth,
            t_sampled,
            b_sampled,
            coefficients_upsampled,
            freq_ranges,
        )
        f2 = plot_wavelet_disc_spectrum(
            args, t_sampled, coefficients_upsampled, freq_ranges
        )

        analysis_figures_wavelet.add_figure([f1], f"wavelet_disc")
        analysis_figures_wavelet.add_figure([f2], f"wavelet_disc_spectrum")
        console.print(f" --- Done --- \n")
    else:
        analysis_figures_wavelet = AnalysisFigures()

    # ! Perform analysis on the result from the DWT
    # analysis = "dft_on_approx_coeff"
    # analysis = "dft_on_all"
    analysis = "dft_x_dwt"
    # analysis = "dwt_x_autocorrelation"
    # if len(coefficients) <= 2:
    #     analysis = "dft_on_all"
    #     console.print(f"[green]Setting analysis to {analysis}")

    # ? Option 1 ("dft_on_approx_coeff"): Execute DFT on approx. coefficients from DWT
    # cont = input("\nContinue with the DFT? [y/n]")
    # if len(cont) == 0 or "y" in cont.lower():
    if "dft_on_approx_coeff" in analysis:
        args.transformation = "dft"
        # Option 1: Filter using wavelet and call DFT on lowest last coefficient
        prediction, analysis_figures_dft, share = ftio_dft(
            args, coefficients_upsampled[0], t_sampled, total_bytes, ranks
        )
        analysis_figures_wavelet += analysis_figures_dft

    # ? Option 2: Find intersection between DWT and DFT
    elif "dft_on_all" in analysis:
        args.transformation = "dft"
        # TODO: For this to be parallel, the generated HTML files need different names as
        #  they are overwritten
        with ProcessPoolExecutor(max_workers=1) as executor:
            # submit futures
            futures = {}
            for i, coeffs in enumerate(coefficients_upsampled):
                tmp_args = copy.deepcopy(args)
                tmp_args.plot_name = f"ftio_dwt{i}_result"
                future = executor.submit(
                    ftio_dft, tmp_args, coeffs, t_sampled, total_bytes, ranks
                )
                futures[future] = i

            # Process futures as they complete
            for future in as_completed(futures):
                prediction, analysis_figures_dft, _ = future.result()
                display_prediction(["ftio"], prediction)
                index = futures[future]
                analyze_correlation(
                    args, prediction, coefficients_upsampled[index], t_sampled
                )
                console.print(f"[green] {index} completed[/]")
            exit()

    # ? Option 3: Find intersection between DWT and DFT
    elif "dft_x_dwt" in analysis:
        args.transformation = "dft"
        # 1): compute DFT on lowest last coefficient
        prediction, analysis_figures_dft, share = ftio_dft(
            args, coefficients_upsampled[0], t_sampled, total_bytes, ranks
        )
        # 2) compare the results
        analyze_correlation(args, prediction, coefficients_upsampled[0], t_sampled)
        if any(x in args.engine for x in ["mat", "plot"]):
            analysis_figures_wavelet += analysis_figures_dft

    # ? Option 4: Apply autocorrelation on low
    elif "dwt_x_autocorrelation" in analysis:
        res = find_fd_autocorrelation(
            args,
            coefficients_upsampled[0],
            args.freq,
            analysis_figures_wavelet,
        )
        exit()

    return prediction, analysis_figures_wavelet, share
