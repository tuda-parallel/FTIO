import numpy as np
import zmq
import msgpack
from rich.console import Console

from ftio.api.metric_proxy.parse_proxy import filter_metrics
from ftio.freq.helper import MyConsole
from ftio.api.metric_proxy.parallel_proxy import execute_parallel, execute

CONSOLE = MyConsole()
CONSOLE.set(True)

CURRENT_ADDRESS = None

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

        print(f"Arguments: {argv}")
        argv.extend(["-e", "no"])

        disable_parallel = req.get("disable_parallel", False)
        ranks = 32

    except Exception as e:
        return msgpack.packb({"error": f"Invalid request: {e}"}, use_bin_type=True)

    try:
        if disable_parallel:
            data = execute(metrics, argv, ranks, show=False)
        else:
            data = execute_parallel(metrics, argv, ranks)
            
        native_data = list(data) if not isinstance(data, list) else data
        native_data = sanitize(native_data)

        return msgpack.packb(native_data, use_bin_type=True)

    except Exception as e:
        print(f"Error during processing: {e}")
        return msgpack.packb({"error": str(e)}, use_bin_type=True)


def main(address: str = "tcp://*:0"):
    """FTIO ZMQ Server entrypoint for Metric Proxy."""
    global CURRENT_ADDRESS
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(address)
    CURRENT_ADDRESS = address

    endpoint = socket.getsockopt(zmq.LAST_ENDPOINT).decode()
    print(endpoint, flush=True)

    console = Console()
    console.print(f"[green]FTIO ZMQ Server listening on {endpoint}[/]")

    while True:
        msg = socket.recv()
        console.print(f"[cyan]Received request ({len(msg)} bytes)[/]")
        reply = handle_request(msg)
        socket.send(reply)

        if reply == b"Address updated":
            console.print(f"[yellow]Updated address to {CURRENT_ADDRESS}[/]")
            socket.close()
            socket = context.socket(zmq.REP)
            socket.bind(CURRENT_ADDRESS)


if __name__ == "__main__":
    main()