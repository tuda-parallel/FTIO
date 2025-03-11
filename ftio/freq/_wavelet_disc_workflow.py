"""Contains functions that execute workflow using the continuous Wavelet Transform.
"""

import time
import copy
from argparse import Namespace
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from ftio.freq._dft import display_prediction
from ftio.freq._wavelet import wavelet_disc
from ftio.freq._wavelet_helpers import (
    wavelet_freq_bands,
    decomposition_level,
    upsample_coefficients,
)
from ftio.freq.autocorrelation import find_fd_autocorrelation
from ftio.freq.discretize import sample_data_and_prepare_plots
from ftio.freq.helper import MyConsole
from ftio.plot.freq_plot import convert_and_plot
from ftio.plot.plot_wavelet_disc import (
    plot_coeffs_reconst_signal,
    plot_wavelet_disc_spectrum,
)
from ftio.freq._dft_workflow import ftio_dft

# from ftio.prediction.helper import[] get_dominant_and_conf


def ftio_wavelet_disc(
    args: Namespace,
    bandwidth: np.ndarray,
    time_b: np.ndarray,
    ranks: int = 0,
    total_bytes: int = 0,
):
    """
    Executes discrete wavelet transformation on the provided bandwidth data.

    Args:
        args: The Namespace object containing configuration options.
        bandwidth (np.ndarray): The bandwidth data to process.
        time_b (np.ndarray): The corresponding time points for the bandwidth data.
        ranks (int): The rank value (default is 0).
        total_bytes (int): total transferred bytes (default is 0).
    """
    # Default values for variables
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

    # Sample the bandwidth evenly spaced in time
    tik = time.time()
    console.print("[cyan]Executing:[/] Discretization\n")
    b_sampled, f_s, [df_out[1], df_out[2]] = sample_data_and_prepare_plots(
        args, bandwidth, time_b, ranks
    )
    console.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")

    tik = time.time()
    console.print(
        f"[cyan]Executing:[/] {args.transformation.upper()} + {args.outlier}\n"
    )

    # discrete wavelet decomposition:
    # https://edisciplinas.usp.br/pluginfile.php/4452162/mod_resource/content/1/V1-Parte%20de%20Slides%20de%20p%C3%B3sgrad%20PSI5880_PDF4%20em%20Wavelets%20-%202010%20-%20Rede_AIASYB2.pdf
    # https://www.youtube.com/watch?v=hAQQwvKsWCY&ab_channel=NathanKutz
    console.print("[green]Performing discrete wavelet decomposition[/]")
    if args.level == 0:
        args.level = decomposition_level(args, len(b_sampled))

    #! calculate the coefficients using the discrete wavelet
    # args.wavelet = "db8"
    # coefficients ->  [cA_n, cD_n, cD_n-1, …, cD2, cD1]
    coefficients = wavelet_disc(b_sampled, args.wavelet, args.level)
    # compute the frequency ranges
    freq_ranges = wavelet_freq_bands(f_s, args.level)
    # Upsample coefficients for equal length
    t_sampled = time_b[0] + np.arange(0, len(b_sampled)) * 1 / f_s
    coefficients_upsampled = upsample_coefficients(
        coefficients, args.wavelet, len(b_sampled)
    )
    # plot functions
    if any(x in args.engine for x in ["mat", "plot"]):
        fig = plot_coeffs_reconst_signal(
            args,
            time_b,
            bandwidth,
            t_sampled,
            b_sampled,
            coefficients_upsampled,
            freq_ranges,
        )
        fig.show()
        fig = plot_wavelet_disc_spectrum(
            args, t_sampled, coefficients_upsampled, freq_ranges
        )
        fig.show()
        # # old
        # cc, f = plot_wave_disc(
        #     b_sampled, coefficients, time_b, args.freq, args.level, args.wavelet, bandwidth
        # )
        # for fig in f:
        #     fig.show()

    analysis = "dft_on_all" 
    # analysis = "dft_on_approx_coeff" 
    # analysis = "dft_x_dwt" 
    # analysis = "dwt_x_autocorrelation" 

    #? Option 1 ("dft_on_approx_coeff"): Execute  DFT on approx. coefficients from DWT
    # cont = input("\nContinue with the DFT? [y/n]")
    # if len(cont) == 0 or "y" in cont.lower():
    if "dft_on_approx_coeff" in analysis:
        args.transformation = "dft"
        # Option 1: Filter using wavelet and call DFT on lowest last coefficient
        prediction, df_out, share = ftio_dft(
            args, coefficients_upsampled[0], t_sampled, total_bytes, ranks
        )
        
    #? Option 2: Find intersection between DWT and DFT
    elif "dft_on_all" in analysis:
        args.transformation = "dft"
        # TODO: For this to be parallel, the generated HTML files need different names as they are overwritten
        with ProcessPoolExecutor(max_workers=4) as executor:
            # submit futures
            futures = {}
            for i, coeffs in enumerate(coefficients_upsampled):
                tmp_args = copy.deepcopy(args)
                tmp_args.plot_name = f"ftio_dwt{i}_result"
                future = executor.submit(ftio_dft, tmp_args, coeffs, t_sampled, total_bytes, ranks)
                futures[future] = i

            # Process futures as they complete 
            for future in as_completed(futures):
                prediction, df_out, _ = future.result()
                convert_and_plot(args, df_out)
                display_prediction(["ftio"], prediction)
                index = futures[future]
                console.print(f"[green] {index} completed[/]")
            exit()

    #? Option 3: Find intersection between DWT and DFT
    elif "dft_x_dwt" in analysis:
        args.transformation = "dft"
        # Option 1: Filter using wavelet and call DFT on lowest last coefficient
        prediction, df_out, share = ftio_dft(
            args, b_sampled, t_sampled, total_bytes, ranks
        )
        display_prediction("ftio", prediction)

    #? Option 4: Apply autocorrelation on low
    elif "dwt_x_autocorrelation" in analysis:
        res = find_fd_autocorrelation(args, coefficients_upsampled[0],args.freq)
        exit()
    return prediction, df_out, share
