from multiprocessing import Manager
from rich.console import Console
import zmq
from ftio.prediction.helper import print_data, export_extrap
from ftio.prediction.async_process import handle_in_process
from ftio.prediction.probability import probability
from ftio.prediction.helper import get_dominant, get_hits
from ftio.api.gekkoFs.ftio_gekko import run
from ftio.prediction.analysis import display_result, save_data, data_analysis
from ftio.prediction.async_process import join_procs
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()
CONSOLE.set(True)

def main(args: list[str] = []) -> None:

    ranks = 0
    args = ["-e", "plotly", "-f", "10"]
    context = zmq.Context()
    socket = context.socket(socket_type=zmq.PULL)
    socket.bind("tcp://*:5555")

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

    if '-zmq' not in args:
        args.extend(['--zmq'])

    # Loop and predict if changes occur
    try:
        while True:
            if procs:
                procs = join_procs(procs)

            # get all messages    
            msgs = []
            ranks = 0
            socks = dict(poller.poll(1000))
            while(socks):
                if socks.get(socket) == zmq.POLLIN:
                    msg = socket.recv(zmq.NOBLOCK)
                    msgs.append(msg)
                    # CONSOLE.print(f"[cyan]Got message {ranks}:[/] {msg}")
                    ranks += 1
                socks = dict(poller.poll(1000))
            if not msgs:
                CONSOLE.print("[red]No messages[/]")
                continue
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
                        t_app
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
    t_app
) -> None:
    console = Console()
    console.print(f"[purple][PREDICTOR] (#{count.value}):[/]  Started")
    # Modify the arguments
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{start_time.value:.2f}"])

    # Perform prediction
    prediction, args  = run(msg, args, b_app,t_app)

    # get data
    freq = get_dominant(prediction)  # just get a single dominant value
    hits = get_hits(prediction, count.value, hits)

    # save prediction results
    save_data(queue, aggregated_bytes, prediction, count, hits)
    # display results
    text = display_result(freq, prediction, count, aggregated_bytes)
    # data analysis to decrease window
    text, start_time.value = data_analysis(args, prediction, freq, count, hits, text)
    console.print(text)
    count.value += 1
    while not queue.empty():
        data.append(queue.get())

    probability(data)


if __name__ == "__main__":
    main()
