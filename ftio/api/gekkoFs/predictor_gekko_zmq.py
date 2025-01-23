import sys
import time
from rich.console import Console
# import numpy as np
import zmq
from ftio.plot.plot_bandwidth import plot_bar_with_rich
from ftio.prediction.shared_resources import SharedResources
from ftio.prediction.helper import print_data#, export_extrap
from ftio.prediction.async_process import handle_in_process
from ftio.prediction.probability_analysis import find_probability
from ftio.prediction.helper import get_dominant_and_conf
from ftio.prediction.analysis import display_result, save_data, window_adaptation
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
    """generates online FTIO predictions and triggers cargo 

    Args:
        args (_type_, optional): FTIO arguments, see "ftio -h".
    """
    #parse arguments
    tmp_args = parse_args(args,'ftio JIT')
    addr = tmp_args.zmq_address
    port = tmp_args.zmq_port
    ranks = 0
    procs = []
    args.extend(["-e", "no"])
    # args.extend(["-e", "no", "-f", "10", "-m", "write","-v"])
    
    #start cargo
    setup_cargo(tmp_args)

    # bind to socket
    socket = bind_socket(addr,port)
    # can be extended to listen to multiple sockets
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    # # Init
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
                        args=(shared_resources, args, msgs),
                    )
                )

    except KeyboardInterrupt:
        trigger.join()
        print_data(shared_resources.data)
        # export_extrap(data=data)
        print("-- done -- ")


def prediction_zmq_process(
    shared_resources, args, msg
) -> None:
    """performs prediction

    Args:
        shared_resources (SharedResources): shared resources among processes
        args (list[str]): additional arguments passed to ftio.py
        msg: zmq message
    """
    t_prediction = time.time()
    console = Console()
    console.print(f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/]  Started")

    # Modify the arguments
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{shared_resources.start_time.value:.2f}"])

    # Perform prediction
    prediction, parsed_args, t_flush = run(msg, args, shared_resources.b_app,shared_resources.t_app)
    shared_resources.t_flush.append(t_flush)

    # plot
    plot_bar_with_rich(shared_resources.t_app,shared_resources.b_app, width_percentage=0.8)

    # get data
    freq, conf = get_dominant_and_conf(prediction)  # just get a single dominant value
    # save prediction results
    save_data( prediction, shared_resources)
    # display results
    text = display_result(freq ,prediction ,shared_resources)
    # data analysis to decrease window thus change start_time
    text += window_adaptation(parsed_args, prediction, freq, shared_resources)
    # print text
    console.print(text)
    
    # save data to queue
    while not shared_resources.queue.empty():
        shared_resources.data.append(shared_resources.queue.get())

    #calculate probability
    prob = find_probability(shared_resources.data, counter = shared_resources.count.value)

    probability = -1
    for p in prob:
        if p.get_freq_prob(freq):
            probability = p.p_freq_given_periodic
            break

    # send data to trigger proc
    shared_resources.sync_trigger.put(
        {
    't_wait':  time.time() ,
    't_end':  prediction['t_end'],
    't_start':  prediction['t_start'],
    't_flush': t_flush + (t_prediction- time.time()),
    'freq': freq,
    'conf': conf,
    'probability': probability,
    'source': f'#{shared_resources.count.value}'
        })

    console.print(f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/] Ended")
    shared_resources.count.value += 1



if __name__ == "__main__":
    main(sys.argv)