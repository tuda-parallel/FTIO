"""
This file provides functions to process input data, perform frequency analysis, and generate predictions
using the FTIO framework. It includes core functionalities for data transformation, frequency analysis,
autocorrelation, and result visualization.
This functions calculates the frequency based on the input data provided.
Currently Darshan, recorder, and traces generated with our internal tool TMIO and the metric proxy are supported.

call ftio -h to see list of supported arguments.

Author: Ahmad Tarraf
Copyright (c) 2025 TU Darmstadt, Germany
Date: Feb 2024

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from __future__ import annotations

import sys
import time
from argparse import Namespace

import numpy as np

from ftio.freq._analysis_figures import AnalysisFigures
from ftio.freq._share_signal_data import SharedSignalData
from ftio.freq.autocorrelation import find_autocorrelation
from ftio.freq.helper import MyConsole
from ftio.freq.prediction import Prediction
from ftio.parse.extract import get_time_behavior_and_args
from ftio.plot.freq_plot import convert_and_plot
from ftio.prediction.unify_predictions import merge_predictions
from ftio.processing.print_output import display_prediction
from ftio.freq.time_window import data_in_time_window
from ftio.freq._wavelet_cont_workflow import ftio_wavelet_cont
from ftio.freq._wavelet_disc_workflow import ftio_wavelet_disc
from ftio.freq._dft_workflow import ftio_dft


def main(
    cmd_input: list[str], msgs=None
) -> tuple[list[Prediction], Namespace]:  # -> dict[Any, Any]:
    """
    Main entry point to process input data, perform frequency analysis, and generate predictions.

    This function handles the following:
    - Parsing input arguments and reading trace data.
    - Performing frequency analysis based on the chosen transformation and mode.
    - Extracting time behavior and performing further analysis.
    - Generating predictions using the core processing logic.
    - Plotting and displaying results.

    Args:
        cmd_input (list[str]): A list of input strings containing the command-line arguments or data.
        msgs (optional): ZMQ message, in case the input is not provided via a file.

    Returns:
        tuple[list[Prediction], Namespace]:
            - A list of Prediction containing the prediction results.
            - A Namespace object with the parsed arguments used in the analysis.
    """

    start = time.time()
    # extract the data
    data, args = get_time_behavior_and_args(cmd_input, msgs)
    console = MyConsole(args.verbose)
    console.print(f"\n[cyan]Data imported in:[/] {time.time() - start:.2f} s")
    console.print(f"[cyan]Frequency Analysis:[/] {args.transformation.upper()}")
    console.print(f"[cyan]Mode:[/] {args.mode}")

    list_analysis_figures = []
    list_predictions = []

    for sim in data:
        # get prediction
        prediction, analysis_figures = core(sim, args)
        # merge results from several files into one
        list_predictions.append(prediction)
        if any(x in args.engine for x in ["mat", "plot"]):
            list_analysis_figures.append(analysis_figures)

    # show merge results
    display_prediction(args, list_predictions)
    # TODO: convert an plot only if autocorrelation is passed
    convert_and_plot(args, list_predictions, list_analysis_figures)
    console.print(f"[cyan]Total elapsed time:[/] {time.time()-start:.3f} s\n")

    return list_predictions, args


def core(sim: dict, args: Namespace) -> tuple[Prediction, AnalysisFigures]:
    """
    FTIO core function that processes data and arguments to generate predictions and results.

    This function processes input data containing time, bandwidth, among others and
    performs operations based on the parsed arguments.

    Args:
        sim (dict): dictionary where each dictionary contains:
            - "time" (np.ndarray): Array of time points.
            - "bandwidth" (np.ndarray): Array of bandwidth values.
            - "total_bytes" (int): Total number of bytes.
            - "ranks" (int): Number of ranks in the system.
        args (Namespace): Parsed arguments to customize the FTIO's behavior.

    Returns:
        tuple[dict, list]: A tuple where:
            - The first element is a dictionary with the obtained predictions (key-value pairs).
            - The second element is used for storing dataframes for plotting.
    """
    if not sim:
        return Prediction(), AnalysisFigures()

    # Perform frequency analysis (dft/wavelet)
    prediction_freq_analysis, analysis_figures, share = freq_analysis(args, sim)
    # Perform autocorrelation if args.autocorrelation is true + Merge the results into a single prediction
    prediction_auto = find_autocorrelation(args, sim, analysis_figures, share)
    # Merge results
    prediction = merge_predictions(
        args, prediction_freq_analysis, prediction_auto, analysis_figures
    )

    return prediction, analysis_figures


def freq_analysis(
    args: Namespace, data: dict
) -> tuple[Prediction, AnalysisFigures, SharedSignalData]:
    """
    Performs frequency analysis (DFT, continuous wavelet, or discrete wavelet) and prepares data for plotting.

    This function analyzes the provided data using the specified frequency technique
    (DFT, continuous wavelet, or discrete wavelet) and then creates a dataframe
    with relevant information for visualization and further analysis.

    Args:
        args (Namespace): Parsed arguments to customize the FTIO's behavior (see io_args.py).
        data (dict[str, np.ndarray]): A dictionary containing the following fields:
            - "bandwidth" (np.ndarray): An array representing the bandwidth values.
            - "time" (np.ndarray): An array representing the time points when the bandwidth changed.
            - "total_bytes" (int): The total number of transferred bytes.
            - "ranks" (int): The number of ranks involved in the I/O operation.

    Raises:
        Exception: If an unsupported method is passed in the `args.transformation`.

    Returns:
        tuple: A tuple containing:
            - Prediction: Contains the prediction results, including:
                - "dominant_freq" (list): The identified dominant frequencies.
                - "conf" (np.ndarray): Confidence values corresponding to the dominant frequencies.
                - "t_start" (int): Start time of the analysis.
                - "t_end" (int): End time of the analysis.
                - "total_bytes" (int): Total bytes involved in the analysis.
            - AnalysisFigures
            - SharedSignalData: Contains sampled data used for sharing (e.g., autocorrelation) containing
            the following fields:
                - "b_sampled" (np.ndarray): The sampled bandwidth data.
                - "freq" (np.ndarray): Frequencies corresponding to the sampled data.
                - "t_start" (int): Start time of the sampled data.
                - "t_end" (int): End time of the sampled data.
                - "total_bytes" (int): Total bytes from the sampled data.
    """

    #! Init
    bandwidth = data["bandwidth"] if "bandwidth" in data else np.array([])
    time_b = data["time"] if "time" in data else np.array([])
    total_bytes = data["total_bytes"] if "total_bytes" in data else 0
    ranks = data["ranks"] if "ranks" in data else 0

    #! Extract relevant data
    bandwidth, time_b, text = data_in_time_window(
        args, bandwidth, time_b, total_bytes, ranks
    )

    #! Perform transformation
    if "dft" in args.transformation:
        prediction, analysis_figures, share = ftio_dft(
            args, bandwidth, time_b, total_bytes, ranks, text
        )

    elif "wave_disc" in args.transformation:
        prediction, analysis_figures, share = ftio_wavelet_disc(
            args, bandwidth, time_b, ranks, total_bytes
        )

    elif "wave_cont" in args.transformation:
        prediction, analysis_figures, share = ftio_wavelet_cont(
            args, bandwidth, time_b, ranks
        )

    elif any(t in args.transformation for t in ("astft", "efd", "vmd")):
        # TODO: add a way to pass the results to FTIO
        try:
            import vmdpy
        except ImportError:
            raise RuntimeError(
                "ASTFT transformation is disabled.\n"
                "Install with: pip install ftio[amd-libs]"
            )

        if "astft" in args.transformation:
            from ftio.freq._astft_workflow import ftio_astft
            import sys

            prediction, analysis_figures, share = ftio_astft(
                args, bandwidth, time_b, total_bytes, ranks, text
            )
            sys.exit()

        if "efd" in args.transformation or "vmd" in args.transformation:
            from ftio.freq._amd_workflow import ftio_amd
            import sys

            prediction, analysis_figures, share = ftio_amd(
                args, bandwidth, time_b, total_bytes, ranks, text
            )
            sys.exit()

    else:
        raise Exception("Unsupported decomposition specified")

    return prediction, analysis_figures, share


def run():
    _ = main(sys.argv)


if __name__ == "__main__":
    _ = main(sys.argv)
