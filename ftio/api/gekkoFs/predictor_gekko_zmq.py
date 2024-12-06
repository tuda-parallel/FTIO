import sys
import time
from multiprocessing import Manager
from rich.console import Console
# import numpy as np
import zmq

from ftio.api.gekkoFs.jit.plot_bandwidth import plot_bar_with_rich
from ftio.prediction.sharedresouces import SharedResources
from ftio.prediction.helper import print_data#, export_extrap
from ftio.prediction.async_process import handle_in_process
from ftio.prediction.probability_analysis import find_probability
from ftio.prediction.helper import get_dominant_and_conf, get_hits
from ftio.prediction.analysis import display_result, save_data, data_analysis
from ftio.prediction.async_process import join_procs
from ftio.prediction.processes_zmq import bind_socket, receive_messages
from ftio.api.gekkoFs.stage_data import setup_cargo, trigger_cargo
from ftio.api.gekkoFs.ftio_gekko import run
from ftio.freq.helper import MyConsole
from ftio.parse.args import parse_args


# T_S = time.time()
CONSOLE = MyConsole()
CONSOLE.set(True)

def main(args: list[str] = sys.argv[1:]) -> None:
    
    #parse arguments
    tmp_args = parse_args(args,'ftio JIT')
    addr = tmp_args.zmq_address
    port = tmp_args.zmq_port
    ranks = 0
    procs = []
    args.extend(["-e", "no", "-f", "10", "-m", "write"])
    # args.extend(["-e", "plotly", "-f", "10", "-m", "write"])

    #start cargo
    setup_cargo(tmp_args)

    # bind to socket
    socket = bind_socket(addr,port)
    # can be extended to listen to multiple sockets
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    # # Init
    # manager = Manager()
    # queue = manager.Queue()
    # data = manager.list()  
    # aggregated_bytes = manager.Value("d", 0.0)
    # hits = manager.Value("d", 0.0)
    # start_time = manager.Value("d", 0.0)
    # count = manager.Value("i", 0)
    # b_app = manager.list()
    # t_app = manager.list()
    # sync_trigger = manager.Queue()
    shared_resources = SharedResources()

    # for Cargo trigger process:
    trigger = handle_in_process(trigger_cargo, args=(shared_resources.sync_trigger, tmp_args),) 

    if "-zmq" not in args:
        args.extend(["--zmq"])

    # Loop and predict if changes occur
    try:
        with CONSOLE.status("[green] started\n",spinner="arrow3") as status:
            while True:
                procs = join_procs(procs)

                # get all messages
                msgs, ranks = receive_messages(socket, poller)

                if not msgs:
                    # CONSOLE.print("[red]No messages[/]")
                    status.update("[cyan]Waiting for messages\n",spinner="dots")
                    continue
                CONSOLE.print(f"[cyan]Got message from {ranks}:[/]")
                status.update("")

                # launch prediction_process
                procs.append(
                    handle_in_process(
                        prediction_zmq_process,
                        args=(shared_resources, msgs, args),
                    )
                )

    except KeyboardInterrupt:
        trigger.join()
        print_data(shared_resources.data)
        # export_extrap(data=data)
        print("-- done -- ")


def prediction_zmq_process(
    shared, msg, args
) -> None:
    """performs prediction

    Args:
        data (_type_): _description_
        queue (_type_): _description_
        count (_type_): _description_
        hits (_type_): _description_
        start_time (_type_): _description_
        aggregated_bytes (_type_): _description_
        args (list[str]): _description_
        msg (_type_): _description_
        b_app (_type_): _description_
        t_app (_type_): _description_
        sync_trigger (_type_): _description_
    """
    t_prediction = time.time()
    console = Console()
    console.print(f"[purple][PREDICTOR] (#{shared.count.value}):[/]  Started")

    # Modify the arguments
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{shared.start_time.value:.2f}"])

    # Perform prediction
    prediction, args, t_flush = run(msg, args, shared.b_app,shared.t_app)

    # plot
    plot_bar_with_rich(shared.t_app,shared.b_app, width_percentage=0.9)

    # get data
    freq, conf = get_dominant_and_conf(prediction)  # just get a single dominant value
    shared.hits = get_hits(prediction, shared.count.value, shared.hits)

    # save prediction results
    save_data(shared.queue, prediction, shared.aggregated_bytes, shared.count, shared.hits)
    # display results
    text = display_result(freq, prediction, shared.count, shared.aggregated_bytes)
    # data analysis to decrease window
    text, shared.start_time.value = data_analysis(args, prediction, freq, shared.count, shared.hits, text)
    # if args.verbose:
    console.print(text)
    shared.count.value += 1

    # save data to queue
    while not shared.queue.empty():
        shared.data.append(shared.queue.get())

    #calculate probability
    prob = find_probability(shared.data)

    probability = -1
    for p in prob:
        if p.get_freq_prob(freq):
            probability = p.p_freq_given_periodic
            break

    # send data to trigger proc
    shared.sync_trigger.put(
        {
    't_wait':  time.time() ,
    't_end':  prediction['t_end'],
    't_start':  prediction['t_start'],
    't_flush': t_flush + (t_prediction- time.time()),
    'freq': freq,
    'conf': conf,
    'probability': probability,
    'source': f'#{shared.count.value}'
        })

    console.print(f"[purple][PREDICTOR] (#{shared.count.value}):[/]  Ended")



if __name__ == "__main__":
    main(sys.argv)