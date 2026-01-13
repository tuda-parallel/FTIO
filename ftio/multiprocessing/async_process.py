"""Performs action async to current process"""

from __future__ import annotations

from multiprocessing import Process
from typing import Callable


def handle_in_process(function: Callable, args) -> Process:
    """Handle function in a dedicated process

    Args:
        function (Callable): function name
        args (argparse): arguments passed to function

    Returns:
        None
    """
    process = Process(target=function, args=args)
    # print(f'Process {process.name} (PID {os.getpid()}) started to execute {function}')
    process.start()
    # print(f'Process {process.name} (PID {os.getpid()}) ended')
    # print(f"Process {process} created")
    return process


def join_procs(procs: list, blocking: bool = True) -> list:
    """
    Joins finished processes safely. Optionally non-blocking.

    Args:
        procs (list): list of multiprocessing.Process objects
        blocking (bool): if True, join finished processes immediately
    Returns:
        list: updated list of alive processes
    """
    alive_procs = []
    for p in procs:
        if p.is_alive():
            alive_procs.append(p)
        else:
            if blocking:
                p.join()  # join if requested
    return alive_procs
