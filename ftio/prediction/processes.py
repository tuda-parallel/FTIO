"""Performs prediction with Pools (ProcessPoolExecutor) and a callback mechanism"""
from __future__ import annotations
import ftio.prediction.monitor as pm
from ftio.prediction.probability_analysis import find_probability
from ftio.prediction.helper import print_data, export_extrap
from ftio.prediction.analysis import ftio_process
from ftio.prediction.async_process import handle_in_process

# from ftio.prediction.async_process import handle_in_process


def predictor_with_processes(
    filename, data, queue, count, hits, start_time, aggregated_bytes, args
):
    """performs prediction in ProcessPoolExecuter. FTIO is a submitted future and probability is calculated as a callback

    Args:   
        filename (str): name of file
        data (Manager().list): List of dicts with all predictions so far
        queue (Manager().Queue): queue for FTIO data
        count (Manager().Value): number of prediction
        hits (Manager().Value): hits indicating how often a dominant frequency was found
        start_time (Manager().Value): start time window for ftio
        aggregated_bytes (Manager().Value): total bytes transferred so far
        args (list[str]): additional arguments passed to ftio
    """
    procs = []
    # Init: Monitor a file
    stamp,_ = pm.monitor(filename, "")

    # Loop and predict if changes occur
    try:
        while True:
            # monitor
            stamp, procs = pm.monitor(filename, stamp, procs)
            # launch prediction_process
            procs.append(
                handle_in_process(
                    prediction_process,
                    args=(data, queue, count, hits, start_time, aggregated_bytes, args)
                )
            )
    except KeyboardInterrupt:
        print_data(data)
        export_extrap(data)
        print("-- done -- ")


def prediction_process(
    data, queue, count, hits, start_time, aggregated_bytes, args: list[str], msgs=None) -> None:
    """Performs prediction made up of two part: (1) Executes FTIO and (2) appends to data the value

    Args:
        data (Manager().list): List of dicts with all predictions so far
        queue (Manager().Queue): queue for FTIO data
        count (Manager().Value): number of prediction
        hits (Manager().Value): hits indicating how often a dominant frequency was found
        start_time (Manager().Value): start time window for ftio
        aggregated_bytes (Manager().Value): total bytes transferred so far
        args (list[str]): additional arguments passed to ftio.py
    """
    ftio_process(queue, count, hits, start_time, aggregated_bytes, args, msgs)
    while not queue.empty():
        data.append(queue.get())

    _ = find_probability(data)
