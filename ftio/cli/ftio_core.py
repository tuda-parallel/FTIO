"""This functions calculates the frequency based on the input data provided. 
Currently Darshan, recorder, and traces generated with our internal tool are supported. 

call ftio -h to see list of supported arguments. 
"""

from __future__ import annotations
from argparse import Namespace
import time
import sys
import numpy as np
from ftio.parse.scales import Scales
from ftio.parse.extract import get_time_behavior
from ftio.plot.freq_plot import convert_and_plot
from ftio.freq.helper import get_mode, MyConsole, merge_results
from ftio.freq.autocorrelation import find_autocorrelation

from ftio.freq._wavelet import decomposition_level, wavelet_disc#,welch
from ftio.plot.plot_wavelet import plot_wave_disc
from ftio.freq._dft import  display_prediction
from ftio.prediction.unify_predictions import merge_predictions
from ftio.freq.time_window import data_in_time_window
from ftio.freq._wavelet_workflow import ftio_wavelet_cont, ftio_wavelet_disc
from ftio.freq._dft_workflow import ftio_dft


def main(cmd_input: list[str], msgs = None):  # -> dict[Any, Any]:
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
        msgs (optional): ZMQ message, in case the input is not provided via a file

    Returns:
        tuple[dict, Namespace]: 
            - A dictionary containing the prediction results.
            - A Namespace object with the parsed arguments used in the analysis.
    """
    # prepare data
    start = time.time()
    data = Scales(cmd_input, msgs)
    data.get_data()
    args = data.args
    df = get_mode(data, args.mode)
    data = get_time_behavior(df)
    console = MyConsole(args.verbose)
    console.print(f"\n[cyan]Data imported in:[/] {time.time() - start:.2f} s")
    console.print(f"[cyan]Frequency Analysis:[/] {args.transformation.upper()}")
    console.print(f"[cyan]Mode:[/] {args.mode}")

    # get prediction
    prediction, dfs = core(data, args)

    # plot and print info
    convert_and_plot(data, dfs, args)
    display_prediction(cmd_input, prediction)
    console.print(f"[cyan]Total elapsed time:[/] {time.time()-start:.3f} s\n")

    return prediction, args


def core(data: list[dict], args:Namespace) -> tuple[dict, list]:
    """
    FTIO core function that processes data and arguments to generate predictions and results.

    This function processes input data containing time, bandwidth, among others and 
    performs operations based on the parsed arguments.

    Args:
        data (list[dict]): A list of dictionaries where each dictionary contains:
            - "time" (np.ndarray): Array of time points.
            - "bandwidth" (np.ndarray): Array of bandwidth values.
            - "total_bytes" (int): Total number of bytes.
            - "ranks" (int): Number of ranks in the system.
        args (Namespace): Parsed arguments to customize the FTIO's behavior.

    Returns:
        tuple[dict, list]: A tuple where:
            - The first element is a dictionary with the obtained predictions (key-value pairs).
            - The second is element is used for storing dataframes for plotting.
    """
    # init
    prediction = {}
    share = {}
    dfs_out = [[],[],[],[]]

    # get predictions
    for sim in data:
        # Perform frequency analysis (dft/wavelet)
        prediction_dft, dfs, share = freq_analysis(args, sim)
        # Perform autocorrelation if args.autocorrelation is true + Merge the results into a single prediction
        prediction_auto = find_autocorrelation(args, sim, share)
        # Merge results
        prediction = merge_predictions(args, prediction_dft, prediction_auto)
        # merge plots
        dfs_out = merge_results(dfs_out, df1=dfs)

    return prediction, dfs_out


def freq_analysis(args:Namespace, data: dict) -> tuple[dict, tuple[list, list, list, list], dict]:
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
            - dict: Contains the prediction results, including:
                - "dominant_freq" (list): The identified dominant frequencies.
                - "conf" (np.ndarray): Confidence values corresponding to the dominant frequencies.
                - "t_start" (int): Start time of the analysis.
                - "t_end" (int): End time of the analysis.
                - "total_bytes" (int): Total bytes involved in the analysis.
            - tuple[list, list, list, list]: Four lists containing data for plotting:
            - dict: Contains sampled data used for sharing (e.g., autocorrelation) containing
            the following fields:
                - "b_sampled" (np.ndarray): The sampled bandwidth data.
                - "freq" (np.ndarray): Frequencies corresponding to the sampled data.
                - "t_start" (int): Start time of the sampled data.
                - "t_end" (int): End time of the sampled data.
                - "total_bytes" (int): Total bytes from the sampled data.
    """

    
    #! Init
    df_out = [[], [], [], []]
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
        prediction, df_out, share = ftio_dft(args, bandwidth,time_b, total_bytes, ranks, text)

    elif "wave_disc" in args.transformation:
        prediction, df_out, share  = ftio_wavelet_disc(args,bandwidth, time_b, ranks, total_bytes)
       

    elif "wave_cont" in args.transformation:
        prediction, df_out, share  = ftio_wavelet_cont(args,bandwidth, time_b, ranks)

    else:
        raise Exception("Unsupported decomposition specified")

    return prediction, df_out, share


def run():
    _ = main(sys.argv)


if __name__ == "__main__":
    _ = main(sys.argv)
