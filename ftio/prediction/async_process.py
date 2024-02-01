"""Performs action async to current process
"""
from __future__ import annotations
from typing import Callable
from multiprocessing import Process

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

def join_procs(procs:list) -> list:
    """joins procs by itterating over list and testing
    that the process finished before joining

    Args:
        procs (list): list of procs to test

    Returns:
        list of new procs
    """
    if procs:
        for p in procs:
            if p.is_alive():
                pass 
                # print(f"Process {p} still working")
            else:
                p.join()
                procs.remove(p)
                # print(f"Process {p} JOINED")
    return procs