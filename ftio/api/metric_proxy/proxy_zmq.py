"""
This file provides a custom ZMQ server implementation for communication with the Metric Proxy.
This includes handling data transmission, deserialization, and serialization from and to the Metric Proxy,
processing requests, answering pings and changing the servers address on request from the Proxy.

Author: Tim Dieringer
Copyright (c) 2025 TU Darmstadt, Germany  
Date: January 2026

Licensed under the BSD 3-Clause License.  
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""
import math
import time
import numpy as np
import zmq
import msgpack
from rich.console import Console

from multiprocessing import Pool, cpu_count
from ftio.api.metric_proxy.parallel_proxy import execute, execute_parallel
from ftio.prediction.tasks import ftio_metric_task, ftio_metric_task_save

from ftio.api.metric_proxy.parse_proxy import filter_metrics
from ftio.freq.helper import MyConsole
import signal

CONSOLE = MyConsole()
CONSOLE.set(True)

CURRENT_ADDRESS = None
IDLE_TIMEOUT = 100
last_request = time.time()

def sanitize(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj


def handle_request(msg: bytes) -> bytes:
    """Handle one FTIO request via ZMQ."""
    global CURRENT_ADDRESS

    if msg == b"ping":
        return b"pong"
    
    if msg.startswith(b"New Address: "):
        new_address = msg[len(b"New Address: "):].decode()
        CURRENT_ADDRESS = new_address
        return b"Address updated"
    
    try:
        req = msgpack.unpackb(msg, raw=False)
        argv = req.get("argv", [])
        raw_metrics = req.get("metrics", [])

        metrics = filter_metrics(raw_metrics, filter_deriv=False)
        print(f"Processing {len(metrics)} metrics")

        print(f"With Arguments: {argv}")
        argv.extend(["-e", "no"])

        disable_parallel = req.get("disable_parallel", False)

        ranks = 32


    except Exception as e:
        return msgpack.packb({"error": f"Invalid request: {e}"}, use_bin_type=True)

    try:
        t = time.process_time()
        if disable_parallel:
            data = execute(metrics, argv, ranks, False)
        else:
            data = execute_parallel(metrics, argv, ranks)
        elapsed_time = time.process_time() - t
        CONSOLE.info(f"[blue]Calculation time: {elapsed_time} s[/]")
        
        native_data = sanitize(list(data))

        return msgpack.packb(native_data, use_bin_type=True)

    except Exception as e:
        print(f"Error during processing: {e}")
        return msgpack.packb({"error": str(e)}, use_bin_type=True)


def main(address: str = "tcp://*:0"):
    """FTIO ZMQ Server entrypoint for Metric Proxy."""
    global CURRENT_ADDRESS, last_request, POOL
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(address)
    CURRENT_ADDRESS = address

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    endpoint = socket.getsockopt(zmq.LAST_ENDPOINT).decode()
    print(endpoint, flush=True)

    console = Console()
    console.print(f"[green]FTIO ZMQ Server listening on {endpoint}[/]")

    try:
        while True:
            if socket.poll(timeout=1000):
                msg = socket.recv()
                console.print(f"[cyan]Received request ({len(msg)} bytes)[/]")
                last_request = time.time()
                reply = handle_request(msg)
                socket.send(reply)

                if reply == b"Address updated":
                    console.print(f"[yellow]Updated address to {CURRENT_ADDRESS}[/]")
                    socket.close()
                    socket = context.socket(zmq.REP)
                    socket.bind(CURRENT_ADDRESS)
            else:
                if time.time() - last_request > IDLE_TIMEOUT:
                    console.print("Idle timeout reached, shutting down server")
                    break
    finally:
        socket.close(linger=0)
        context.term()

        
def shutdown_handler(signum, frame):
    raise SystemExit



if __name__ == "__main__":
    main()