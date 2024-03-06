"""Performs prediction with Pools (ProcessPoolExecutor) and a callback mechanism"""
from __future__ import annotations
import zmq
from ftio.prediction.async_process import join_procs
from ftio.prediction.processes import prediction_process
from ftio.prediction.helper import print_data, export_extrap
from ftio.prediction.async_process import handle_in_process

def predictor_with_processes_zmq(
    data, queue, count, hits, start_time, aggregated_bytes, args
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
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect("tcp://127.0.0.1:5555")

    if "-zmq" not in args:
        args.extend(["--zmq"])
    
    # Loop and predict if changes occur
    try:
        while True:
            if procs:
                procs = join_procs(procs)
            msg = socket.recv()
            procs.append(
                handle_in_process(
                    prediction_process,
                    args=(data, queue, count, hits, start_time, aggregated_bytes, args, msg)
                )
            )
    except KeyboardInterrupt:
        print_data(data)
        export_extrap(data)
        print("-- done -- ")


