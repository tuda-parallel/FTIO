import time
import os
import subprocess
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
T_S = time.time()

def main(args: list[str] = []) -> None:
    if CARGO:
        os.system(f"{CARGO_PATH}/cargo_ftio --server {CARGO_SERVER} -c -1 -p -1 -t 10000")
        os.system(f"{CARGO_PATH}/cpp --server {CARGO_SERVER} --input /data --output ~/stage-out --if gekkofs --of parallel")
    ranks = 0
    args.extend(["-e", "plotly", "-f", "10", "-m", "write"])
    context = zmq.Context()
    socket = context.socket(socket_type=zmq.PULL)
    # addr = "*"
    addr = "127.0.0.1"
    # addr = "10.81.3.158"
    port = "5555"
    
    try:
        socket.bind(f"tcp://{addr}:{port}")
    except zmq.error.ZMQError as e:
        CONSOLE.print(f"[yellow]Error encountered:\n{e}[/]")
        CONSOLE.print("[yellow]Wrong ip address. FTIO is running on:[/]")
        addr = str(subprocess.check_output("ip addr | grep 'inet 10' | awk  '{print $2}'", shell=True))
        end   = addr.rfind("/")
        start = addr.find("'")
        addr = addr[start+1:end]
        CONSOLE.print("[bold green]correcting Listing IP address[/]")
        socket.bind(f"tcp://{addr}:{port}")
    
    CONSOLE.print(f"[green]FTIO is running on: {addr}[/]")
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

    # for Cargo trigger process:
    sync_trigger = manager.Queue()
    trigger = handle_in_process(trigger_cargo, args=(sync_trigger,)) 
    
    

    if "-zmq" not in args:
        args.extend(["--zmq"])

    # Loop and predict if changes occur
    try:
        with CONSOLE.status("[green] started\n",spinner="arrow3") as status:
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
                    status.update("[cyan]Waiting for messages\n",spinner="dots")
                    continue
                CONSOLE.print(f"[cyan]Got message from {ranks}:[/]")
                status.update("")

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
                            sync_trigger
                        ),
                    )
                )

    except KeyboardInterrupt:
        trigger.join()
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
    sync_trigger
) -> None:
    t_prediction = time.time()
    console = Console()
    console.print(f"[purple][PREDICTOR] (#{count.value}):[/]  Started")

    # Modify the arguments
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{start_time.value:.2f}"])

    # Perform prediction
    prediction, args, t_flush = run(msg, args, b_app, t_app)

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

    # save data to queue
    while not queue.empty():
        data.append(queue.get())

    #calculate probability
    prob = find_probability(data)

    probability = -1
    for p in prob:
        if p.get_freq_prob(freq):
            probability = p.p_freq_given_periodic
            break

    # send data to trigger proc
    sync_trigger.put(
        {
    't_wait':  time.time() ,
    't_end':  prediction['t_end'],
    't_flush': t_flush + (t_prediction- time.time()),
    'freq': freq,
    'conf': conf,
    'probability': probability
        })
        
    CONSOLE.print("[bold purple]Ended[/]")



def trigger_cargo(sync_trigger):
    """sends cargo calls

    Args:
        sync_trigger (_type_): _description_
    """
    #Maybe needs Mutex
    # TODO: replace sync_trigger by a queue, as freq can be overwritten by the most recent prediction
    while True:
        try:            
            if not sync_trigger.empty():
                element = sync_trigger.get()
                t = time.time() - element['t_wait']  # add this time to t_flush (i.e., the time waiting)
                # CONSOLE.print(f"[bold green][Trigger] queue wait time = {t:.3f} s[/]\n")
                if not np.isnan(element['freq']): 
                    target_time = element['t_end'] + 1/element['freq']
                    geko_elapsed_time = element['t_flush'] + t  # t  is the waiting time in this function
                    remaining_time = (target_time - geko_elapsed_time ) 
                    CONSOLE.print(f"[bold green][Trigger] Target time = {target_time:.3f} -- Gekko time = {geko_elapsed_time:.3f} -> sending message in {remaining_time:.3f} s[/]\n")
                    if remaining_time > 0:
                        countdown = time.time() + remaining_time
                        # wait till the time elapses 
                        while time.time() < countdown:
                            pass
                        # send the stuff
                        # TODO: could check if there is a new value in the queue and if so, skip this prediction
                        if CARGO:
                            os.system(f"{CARGO_PATH}/cargo_ftio --server {CARGO_SERVER} -c {element['conf']} -p {element['probability']} -t {1/element['freq']} ")
                        CONSOLE.print(f"[bold green][Trigger] >>>> Executed cargo_ftio: {CARGO_PATH}/cargo_ftio --server {CARGO_SERVER} -c {element['conf']:.3f} -p {element['probability']:.3f} -t {1/element['freq']:.3f}  [/]\n")
            time.sleep(0.01)
        except KeyboardInterrupt:
            exit()


if __name__ == "__main__":
    main()
