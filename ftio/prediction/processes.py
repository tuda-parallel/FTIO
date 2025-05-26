"""Performs prediction with Pools (ProcessPoolExecutor) and a callback mechanism"""

from __future__ import annotations

import ftio.prediction.monitor as pm
from ftio.multiprocessing.async_process import handle_in_process
from ftio.prediction.analysis import ftio_process
from ftio.prediction.helper import export_extrap, print_data
from ftio.prediction.probability_analysis import find_probability

# from ftio.prediction.async_process import handle_in_process


def predictor_with_processes(shared_resources, args):
    """performs prediction in ProcessPoolExecuter. FTIO is a submitted future and probability is calculated as a callback

    Args:
        shared_resources (SharedResources): shared resources among processes
        args (list[str]): additional arguments passed to ftio
    """
    filename = args[1]
    procs = []
    # Init: Monitor a file
    stamp, _ = pm.monitor(filename, "")

    # Loop and predict if changes occur
    try:
        while True:
            # monitor
            stamp, procs = pm.monitor(filename, stamp, procs)
            # launch prediction_process
            procs.append(
                handle_in_process(
                    prediction_process, args=(shared_resources, args)
                )
            )
    except KeyboardInterrupt:
        print_data(shared_resources.data)
        export_extrap(shared_resources.data)
        print("-- done -- ")


def prediction_process(shared_resources, args: list[str], msgs=None) -> None:
    """Performs prediction made up of two part: (1) Executes FTIO and (2) appends to data the value

    Args:
        shared_resources (SharedResources): shared resources among processes
        args (list[str]): additional arguments passed to ftio.py
        msg: zmq message
    """
    ftio_process(shared_resources, args, msgs)
    while not shared_resources.queue.empty():
        shared_resources.data.append(shared_resources.queue.get())

    _ = find_probability(
        shared_resources.data, counter=shared_resources.count.value
    )
    shared_resources.count.value += 1
