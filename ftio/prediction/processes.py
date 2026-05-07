"""
Performs prediction with Pools (ProcessPoolExecutor) and a callback mechanism

Author: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Version: 0.0.8
Date: Feb 2024

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from __future__ import annotations

import ftio.prediction.monitor as pm
from ftio.multiprocessing.async_process import handle_in_process
from ftio.prediction.helper import export_extrap, print_data
from ftio.prediction.online_analysis import ftio_process
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
                handle_in_process(prediction_process, args=(shared_resources, args))
            )
    except KeyboardInterrupt:
        print_data(shared_resources.data)
        export_extrap(shared_resources.data)
        _export_phase_automaton(shared_resources)
        print("-- done -- ")


def _export_phase_automaton(shared_resources) -> None:
    """Export the phase automaton to JSON if it was built during this run."""
    aut = shared_resources.online_detection.get("pa_automaton", None)
    if aut is None:
        return
    path = shared_resources.online_detection.get("pa_export", "./phase_automaton.json")
    try:
        aut.save_json(path)
    except Exception as exc:
        print(f"[PhaseAutomaton] Could not export to {path}: {exc}")


def prediction_process(shared_resources, args: list[str], msgs=None) -> None:
    """Performs prediction made up of two parts: (1) Executes FTIO and (2) appends to data the value

    Args:
        shared_resources (SharedResources): shared resources among processes
        args (list[str]): additional arguments passed to ftio.py
        msg: zmq message
    """
    ftio_process(shared_resources, args, msgs)
    while not shared_resources.queue.empty():
        shared_resources.data.append(shared_resources.queue.get())

    _ = find_probability(shared_resources.data, counter=shared_resources.count.value)
    shared_resources.count.value += 1
