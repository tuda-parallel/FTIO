"""Contains functions that execute workflow using the continuous Wavelet Transform.
"""
import time
from argparse import Namespace
import pandas as pd
import numpy as np
from ftio.freq._wavelet import decomposition_level, wavelet_cont, wavelet_disc
from ftio.freq.discretize import sample_data_and_prepare_plots
from ftio.freq.helper import MyConsole
from ftio.plot.plot_wavelet import plot_wave_cont, plot_wave_disc
from ftio.freq._dft_workflow import ftio_dft


def ftio_wavelet_cont(args:Namespace, bandwidth: np.ndarray, time_b: np.ndarray, ranks: int = 0):
    """
    Executes continuous wavelet transformation on the provided bandwidth data.

    Args:
        args: The Namespace object containing configuration options.
        bandwidth (np.ndarray): The bandwidth data to process.
        time_b (np.ndarray): The corresponding time points for the bandwidth data.
        ranks (int): The rank value (default is 0).
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

    #! Sample the bandwidth evenly spaced in time
    tik = time.time()
    console.print("[cyan]Executing:[/] Discretization\n")
    b_sampled, sampling_frequency, [df_out[1], df_out[2]] = sample_data_and_prepare_plots(args, bandwidth, time_b, ranks
    )   
    console.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")

    tik = time.time()
    console.print(
        f"[cyan]Executing:[/] {args.transformation.upper()} + {args.outlier}\n"
    )
    
    #! Continuous Wavelet transform
    wavelet = "morl"
    # wavelet = 'cmor'
    # wavelet = 'mexh'
    if args.level == 0:
        args.level = decomposition_level(args, len(b_sampled), wavelet)

    # TODO: use DFT to select the scales (see tmp/test.py)
    scale = np.arange(1, args.level)  # 2** mimcs the DWT
    coefficients, frequencies = wavelet_cont(b_sampled, wavelet, scale, args.freq)
    _ = plot_wave_cont(b_sampled, frequencies, args.freq, time_b, coefficients)
    # TODO: Find a way to process this info
    dominant_index = []

    if any(x in args.engine for x in ["mat", "plot"]):
        df_out[0], df_out[3] = prepare_plot_wavelet_cont(
            frequencies, np.zeros(len(frequencies)), dominant_index, coefficients, b_sampled, ranks
        )

    console.print(
        f"\n[cyan]{args.transformation.upper()} + {args.outlier} finished:[/] {time.time() - tik:.3f} s"
    )
    return prediction, df_out , share


def ftio_wavelet_disc(args:Namespace, bandwidth: np.ndarray, time_b: np.ndarray, ranks: int = 0, total_bytes: int = 0):
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
    b_sampled, freq, [df_out[1], df_out[2]] = sample_data_and_prepare_plots(args, bandwidth, time_b, ranks
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
    wavelet = "db1"  # dmey might be better https://pywavelets.readthedocs.io/en/latest/ref/wavelets.html
    if args.level == 0:
        args.level = decomposition_level(args,len(b_sampled), wavelet)  

    coffs = wavelet_disc(b_sampled, wavelet, args.level)
    cc, f = plot_wave_disc(
        b_sampled, coffs, time_b, args.freq, args.level, wavelet, bandwidth
    )
    for fig in f:
        fig.show()

    cont = input("\nContinue with the DFT? [y/n]")

    if len(cont) == 0 or "y" in cont.lower():
        args.transformation = "dft"
        n = len(b_sampled)
        time_dft =  time_b[0] + 1/freq * np.arange(0, n)
        bandwidth = cc[0]

        # Option 1: Filter using wavelet and call DFT on lowest last coefficient
        prediction, df_out, share = ftio_dft(args, bandwidth, time_dft, total_bytes, ranks)   
        # TODO: Option 2: Find intersection between DWT and DFT


    
    return prediction, df_out , share


def prepare_plot_wavelet_cont(
    frequencies:np.ndarray,
    conf:np.ndarray,
    dominant_index:list[float],
    coefficients:np.ndarray,
    b_sampled:np.ndarray,
    ranks:int,
) ->  tuple[list[pd.DataFrame], list[pd.DataFrame]]:
    """
    Prepares data for plotting the Discrete Fourier Transform (DFT) by creating two DataFrames.

    Args:
        frequencies: An array of frequency values.
        conf: An array of confidence values corresponding to the frequencies.
        dominant_index: The index (or indices) of the dominant frequency component.
        amp: An array of amplitudes corresponding to the frequencies.
        phi: An array of phase values corresponding to the frequencies.
        b_sampled: An array of sampled bandwidth values.
        ranks: The number of ranks.

    Returns:
        tuple[list[pd.DataFrame], list[pd.DataFrame]]: A tuple containing two lists of DataFrames:
            - The first list contains a DataFrame with amplitude (A), phase (phi), sampled bandwidth (b_sampled), ranks, frequency (freq), 
            period (T), and confidence (conf) values.
            - The second list contains a DataFrame with the dominant frequency, its index (k), its confidence, and the ranks.
    """
    df0 = []
    df1 = []

    # Automatically handle multi-dimensional coefficients
    df_data = {
    **{f"coefficients_dim_{i+1}": value for i, value in enumerate(coefficients)},
    **{f"frequencies_dim_{i+1}": np.repeat(value,len(b_sampled)) for i, value in enumerate(frequencies)},
    "b_sampled": b_sampled,
    "ranks": np.repeat(ranks, len(b_sampled)), 
    "k": np.arange(0, len(b_sampled)),       
    }
    # Append the DataFrame
    df0.append(pd.DataFrame(df_data))

    df1.append(
        pd.DataFrame(
            {
                "dominant": frequencies[dominant_index],
                "k": dominant_index,
                "conf": conf[dominant_index],
                "ranks": np.repeat(ranks, len(dominant_index)),
            }
        )
    )
    return df0, df1