import json
import zmq
from rich.console import Console

from ftio.api.metric_proxy.helper import NpArrayEncode, data_to_json
from ftio.api.metric_proxy.parse_proxy import filter_metrics, load_proxy_trace_stdin
from ftio.freq.helper import MyConsole
from ftio.parse.args import parse_args
from ftio.api.metric_proxy.parallel_proxy import execute_parallel, execute

CONSOLE = MyConsole()
CONSOLE.set(True)


def handle_request(msg: str) -> str:
    """Handle one FTIO request via ZMQ."""
    if msg == "ping":
        return "pong"
    
    try:
        req = json.loads(msg)
        argv = req.get("argv", [])
        raw_metrics = req.get("metrics", [])

        metrics = filter_metrics(raw_metrics, filter_deriv=False)

        print(f"Arguments: {argv}")
        argv.extend(["-e", "no"])

        
        disable_parallel = req.get("disable_parallel", False)
        ranks = 32

    except (KeyError, json.JSONDecodeError) as e:
        return json.dumps({"error": f"Invalid request: {e}"})

    try:
        if disable_parallel:
            data = execute(metrics, argv, ranks)
        else:
            data = execute_parallel(metrics, argv, ranks)
            
        native_data = list(data) if not isinstance(data, list) else data

        return json.dumps(native_data, cls=NpArrayEncode)

    except Exception as e:
        return json.dumps({"error": str(e)})


def main(address: str = "tcp://*:5555"):
    """FTIO ZMQ Server entrypoint for Metric Proxy."""
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(address)

    console = Console()
    console.print(f"[green]FTIO ZMQ Server listening on {address}[/]")

    while True:
        msg = socket.recv_string()
        console.print(f"[cyan]Received request ({len(msg)} bytes)[/]")
        reply = handle_request(msg)
        socket.send_string(reply)


if __name__ == "__main__":
    main()