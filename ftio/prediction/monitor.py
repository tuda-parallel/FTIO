from __future__ import annotations
import os
import fcntl
import signal
from time import sleep
from rich.console import Console
from ftio.prediction.async_process import join_procs
from time import sleep

CONSOLE = Console()


def monitor(name: str, _cached_stamp: str, procs: list = []) ->  tuple[str, list]:
    """Monitors a file for change and can optionally join processes in the mean time

    Args:
        name (str): filename
        _cached_stamp (str): time stamp since last time
        procs (list, optional): List of proccess to join. Defaults to [].

    Returns:
        str: _description_
    """
    return monitor_stat(name, _cached_stamp, procs)
    # try:
    #     return monitor_stat(name, _cached_stamp, procs)
    # finally:
    #     return monitor_fcntl(name, _cached_stamp, procs)


#! Method 1
def monitor_stat(name: str, _cached_stamp: str, procs: list) -> tuple[str, list]:
    """Monitors a file for changes

    Args:
        name (str): _description_
        _cached_stamp (str): change time stamp
        procs: list or process

    Returns:
        str: _description_
    """
    if _cached_stamp == "":
        stream = os.popen(f"stat -c %z {name} 2>&1")
        stamp = stream.read()
        CONSOLE.print(f"[purple][PREDICTOR]:[/] Monitoring file {name}")
        CONSOLE.print(f"[purple][PREDICTOR]:[/] Stamp is {stamp}")
        return stamp, procs
    else:
        sleep(1)
        while True:
            procs = join_procs(procs)
            stream = os.popen(f"stat -c %z {name} 2>&1")
            stamp = stream.read()
            if stamp != _cached_stamp:
                CONSOLE.print(
                    f"\n[purple][PREDICTOR]:[/] [red bold]Stamp changed[/] to {stamp}"
                )
                sleep(0.2)
                return stamp, procs


#! Method 2
def monitor_fcntl(name: str, _cached_stamp: str, procs: list) ->  tuple[str, list]:
    if _cached_stamp == 0:
        return "", procs

    w = watcher(name)
    signal.signal(signal.SIGIO, w.handler)
    fd = os.open(w.path, os.O_RDONLY)
    fcntl.fcntl(fd, fcntl.F_SETSIG, 0)
    fcntl.fcntl(
        fd,
        fcntl.F_NOTIFY,
        fcntl.DN_ACCESS
        | fcntl.DN_MODIFY
        | fcntl.DN_CREATE
        | fcntl.DN_DELETE
        | fcntl.DN_RENAME
        | fcntl.DN_ATTRIB
        | fcntl.DN_MULTISHOT,
    )
    while w.flag:
        sleep(0.1)
        procs = join_procs(procs)

    return str(w.stamp),procs


class watcher:
    def __init__(self, name):
        self.flag = True
        if "/" in name:
            index = name.rfind("/")
            self.path = name[:index]
            self.name = name[index + 1 :]
        else:
            self.path = os.getcwd()
            self.name = name
        self.absolute_name = f"{self.path}/{self.name}"
        print(f"Monitoring file {self.absolute_name} in path:{self.path}")
        self.stamp = os.stat(self.absolute_name).st_mtime
        CONSOLE.print(f"[purple][PREDICTOR]:[/] Stamp is {self.stamp}")

    def handler(self, signum, path):
        CONSOLE.print(f"[purple][PREDICTOR]:[/] Folder {path} modified ")
        stamp = os.stat(self.absolute_name).st_mtime
        if self.stamp != stamp:
            self.flag = False
            CONSOLE.print(
                f"\n[purple][PREDICTOR]:[/] [red bold]Stamp changed[/] to {stamp}"
            )
