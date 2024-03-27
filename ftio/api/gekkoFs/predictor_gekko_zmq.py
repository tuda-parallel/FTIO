import time
import os
from multiprocessing import Manager
from rich.console import Console
import numpy as np
import zmq
from ftio.prediction.helper import print_data, export_extrap
from ftio.prediction.async_process import handle_in_process
from ftio.prediction.probability_analysis import find_probability
from ftio.prediction.helper import get_dominant_and_conf, get_hits
from ftio.api.gekkoFs.ftio_gekko import run
from ftio.prediction.analysis import display_result, save_data, data_analysis
from ftio.prediction.async_process import join_procs
from ftio.freq.helper import MyConsole



CONSOLE = MyConsole()
CONSOLE.set(True)
CARGO = False
CARGO_PATH = "/beegfs/home/Shared/admire/JIT/iodeps/bin"
CARGO_SERVER = "tcp://127.0.0.1:62000"

def main(args: list[str] = []) -> None:
    if CARGO:
        os.system(f"{CARGO_PATH}/cargo_ftio --server {CARGO_SERVER} -c -1 -p -1 -t 10000")
        os.system(f"{CARGO_PATH}/cpp --server {CARGO_SERVER} --input /data --output ~/stage-out --if gekkofs --of parallel")
    ranks = 0
    args = ["-e", "plotly", "-f", "10", "-m", "write"]
    context = zmq.Context()
    socket = context.socket(socket_type=zmq.PULL)
    # socket.bind("tcp://127.0.0.1:5555")
    # socket.bind("tcp://*:5555")
    socket.bind("tcp://10.81.4.159:5555")

    # can be extended to listen to multiple sockets
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    # Init
    manager = Manager()
    queue = manager.Queue()
    data = manager.list()  # stores prediction
    aggregated_bytes = manager.Value("d", 0.0)
    hits = manager.Value("d", 0.0)
    start_time = manager.Value("d", 0.0)
    count = manager.Value("i", 0)
    procs = []
    b_app = manager.list()
    t_app = manager.list()

    if "-zmq" not in args:
        args.extend(["--zmq"])

    # Loop and predict if changes occur
    try:
        with CONSOLE.status("[gree] started\n",spinner="arrow3") as status:
            while True:
                if procs:
                    procs = join_procs(procs)

                # get all messages
                msgs = []
                ranks = 0
                socks = dict(poller.poll(1000))
                start = time.time()
                while socks and time.time() < start + 0.5:
                    if socks.get(socket) == zmq.POLLIN:
                        msg = socket.recv(zmq.NOBLOCK)
                        msgs.append(msg)
                        # CONSOLE.print(f"[cyan]Got message {ranks}:[/] {msg}")
                        ranks += 1
                    socks = dict(poller.poll(1000))

                if not msgs:
                    # CONSOLE.print("[red]No messages[/]")
                    status.update("[bold cyan] Waiting for messages\n",spinner="dots")
                    continue
                status.update("")
                CONSOLE.print(f"[cyan]Got message from {ranks}:[/]")
                CONSOLE.print("[green]All message received[/]")

                # launch prediction_process
                procs.append(
                    handle_in_process(
                        prediction_zmq_process,
                        args=(
                            data,
                            queue,
                            count,
                            hits,
                            start_time,
                            aggregated_bytes,
                            args,
                            msgs,
                            b_app,
                            t_app,
                        ),
                    )
                )

    except KeyboardInterrupt:
        print_data(data)
        export_extrap(data=data)
        print("-- done -- ")


def prediction_zmq_process(
    data,
    queue,
    count,
    hits,
    start_time,
    aggregated_bytes,
    args: list[str],
    msg,
    b_app,
    t_app,
) -> None:
    console = Console()
    console.print(f"[purple][PREDICTOR] (#{count.value}):[/]  Started")

    # Modify the arguments
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{start_time.value:.2f}"])

    # Perform prediction
    prediction, args = run(msg, args, b_app, t_app)

    # get data
    freq, conf = get_dominant_and_conf(prediction)  # just get a single dominant value
    hits = get_hits(prediction, count.value, hits)

    # save prediction results
    save_data(queue, prediction, aggregated_bytes, count, hits)
    # display results
    text = display_result(freq, prediction, count, aggregated_bytes)
    # data analysis to decrease window
    text, start_time.value = data_analysis(args, prediction, freq, count, hits, text)
    console.print(text)
    count.value += 1

    while not queue.empty():
        data.append(queue.get())

    prob = find_probability(data)

    probability = -1
    for p in prob:
        if p.get_freq_prob(freq):
            probability = p.p_freq_given_periodic
            break

    if CARGO and not np.isnan(freq):
        os.system(f"{CARGO_PATH}/cargo_ftio --server {CARGO_SERVER} -c {conf} -p {probability} -t {1/freq} ")

if __name__ == "__main__":
    main()
