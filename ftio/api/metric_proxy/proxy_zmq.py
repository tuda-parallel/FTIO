import math
import time
import numpy as np
import zmq
import msgpack
from rich.console import Console

from multiprocessing import Pool, cpu_count
from ftio.prediction.tasks import ftio_metric_task, ftio_metric_task_save

from ftio.api.metric_proxy.parse_proxy import filter_metrics
from ftio.freq.helper import MyConsole
import signal

CONSOLE = MyConsole()
CONSOLE.set(True)

CURRENT_ADDRESS = None
IDLE_TIMEOUT = 100
last_request = time.time()

POOL = None

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


    except Exception as e:
        return msgpack.packb({"error": f"Invalid request: {e}"}, use_bin_type=True)

    try:
        t = time.process_time()
        data = execute_parallel(metrics, argv)
        elapsed_time = time.process_time() - t
        CONSOLE.info(f"[blue]Calculation time: {elapsed_time} s[/]")
        
        native_data = sanitize(data)

        return msgpack.packb(native_data, use_bin_type=True)

    except Exception as e:
        print(f"Error during processing: {e}")
        return msgpack.packb({"error": str(e)}, use_bin_type=True)

def execute_parallel(metrics: dict, argv: list):
    global POOL
    
    cpu_workers = max(1, cpu_count() - 2)
    batch_size = max(1, math.ceil(len(metrics) / cpu_workers))
    results = []

    metric_items = list(metrics.items())
    batches = [metric_items[i:i+batch_size] for i in range(0, len(metric_items), batch_size)]

    batch_results = POOL.starmap(
        ftio_metric_task_batch,
        [(batch, argv) for batch in batches]
    )

    for br in batch_results:
        results.extend(br)

    return results

def ftio_metric_task_batch(batch, argv):
    batch_results = []
    for metric, arrays in batch:
        batch_results.extend(ftio_metric_task_save(metric, arrays, argv))
    return batch_results

def ftio_metric_task_save(
    metric: str,
    arrays: np.ndarray,
    argv: list,
    show: bool = False,
) -> None:
    ranks = 32
    prediction = ftio_metric_task(metric, arrays, argv, ranks, show)
    names = []
    result = []
    if prediction.top_freqs:
        freqs = prediction.top_freqs["freq"]
        amps  = prediction.top_freqs["amp"]
        phis  = prediction.top_freqs["phi"]

        for f, a, p in zip(freqs, amps, phis):
            names.append(prediction.get_wave_name(f, a, p))

        result.append(
            {
                "metric": f"{metric}",
                "dominant_freq": prediction.dominant_freq,
                "conf": prediction.conf,
                "amp": prediction.amp,
                "phi": prediction.phi,
                "t_start": prediction.t_start,
                "t_end": prediction.t_end,
                "total_bytes": prediction.total_bytes,
                "ranks": prediction.ranks,
                "freq": float(prediction.freq),
                "top_freq": prediction.top_freqs,
                "n_samples": prediction.n_samples,
                "wave_names": names,
            }
        )
    else:
        CONSOLE.info(f"\n[yellow underline]Warning: {metric} returned {prediction}[/]")

    return result

def main(address: str = "tcp://*:0"):
    """FTIO ZMQ Server entrypoint for Metric Proxy."""
    global CURRENT_ADDRESS, last_request, POOL
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(address)
    CURRENT_ADDRESS = address

    POOL = Pool(processes=cpu_count() - 2, maxtasksperchild=500)

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
        POOL.close()
        POOL.join()
        socket.close(linger=0)
        context.term()

        
def shutdown_handler(signum, frame):
    raise SystemExit



if __name__ == "__main__":
    main()