import sys
import time
import os
from multiprocessing import Manager
from rich.console import Console
import numpy as np
import zmq
from ftio.prediction.helper import print_data#, export_extrap
from ftio.prediction.async_process import handle_in_process
from ftio.prediction.probability_analysis import find_probability
from ftio.prediction.helper import get_dominant_and_conf, get_hits
from ftio.api.gekkoFs.ftio_gekko import run
from ftio.prediction.analysis import display_result, save_data, data_analysis
from ftio.prediction.async_process import join_procs
from ftio.freq.helper import MyConsole
from ftio.parse.args import parse_args
from ftio.prediction.processes_zmq import bind_socket, receive_messages


T_S = time.time()
CONSOLE = MyConsole()
CONSOLE.set(True)
CARGO = True

def main(args: list[str] = sys.argv[1:]) -> None:
    
    #parse arguments
    tmp_args = parse_args(args,'ftio JIT')
    addr = tmp_args.zmq_address
    port = tmp_args.zmq_port

    #start cargo
    setup_cargo(tmp_args)

    ranks = 0
    args.extend(["-e", "no", "-f", "10", "-m", "write"])
    # args.extend(["-e", "plotly", "-f", "10", "-m", "write"])

    # bind to socket
    socket = bind_socket(addr,port)
    # can be extended to listen to multiple sockets
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    # Init
    manager = Manager()
    queue = manager.Queue()
    data = manager.list()  
    aggregated_bytes = manager.Value("d", 0.0)
    hits = manager.Value("d", 0.0)
    start_time = manager.Value("d", 0.0)
    count = manager.Value("i", 0)
    procs = []
    b_app = manager.list()
    t_app = manager.list()

    # for Cargo trigger process:
    sync_trigger = manager.Queue()
    trigger = handle_in_process(trigger_cargo, args=(sync_trigger, tmp_args),) 

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
        # export_extrap(data=data)
        print("-- done -- ")


def prediction_zmq_process(
    data,
    queue,
    count,
    hits,
    start_time,
    aggregated_bytes,
    args,
    msg,
    b_app,
    t_app,
    sync_trigger
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
    # if args.verbose:
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
    't_start':  prediction['t_start'],
    't_flush': t_flush + (t_prediction- time.time()),
    'freq': freq,
    'conf': conf,
    'probability': probability,
    'source': f'#{count.value}'
        })

    console.print(f"[purple][PREDICTOR] (#{count.value}):[/]  Ended")



def trigger_cargo(sync_trigger,args):
    """sends cargo calls. For that in extracts the predictions from `sync_trigger` and examines it. 

    Args:
        sync_trigger (_type_): _description_
    """
    while True:
        try:
            if not sync_trigger.empty():
                skip_flag = False 
                prediction = sync_trigger.get()
                t = time.time() - prediction['t_wait']  # time waiting so far
                # CONSOLE.print(f"[bold green][Trigger] queue wait time = {t:.3f} s[/]\n")
                if not np.isnan(prediction['freq']):
                    #? 1) Find estimated number of phases and skip in case less than 1
                    # n_phases = (prediction['t_end']- prediction['t_start'])*prediction['freq']
                    # if n_phases <= 1:
                    #     CONSOLE.print(f"[bold green][Trigger] Skipping this prediction[/]\n")
                    #     continue
                    
                    #? 2) Time analysis to find the right instance when to send the data
                    target_time = prediction['t_end'] + 1/prediction['freq']
                    geko_elapsed_time = prediction['t_flush'] + t  # t  is the waiting time in this function. t_flush contains the overhead of ftio + when the data was flushed from gekko
                    remaining_time = (target_time - geko_elapsed_time ) 
                    CONSOLE.print(f"[bold green][Trigger {prediction['source']}][/][green] Target time = {target_time:.3f} -- Gekko time = {geko_elapsed_time:.3f} -> sending cmd in {remaining_time:.3f} s[/]\n")
                    if remaining_time > 0:
                        countdown = time.time() + remaining_time
                        # wait till the time elapses:
                        while time.time() < countdown:
                            pass
                            #? 3) Skip in case new prediction is available  
                            # if not sync_trigger.empty():
                            #     skip_flag = True

                        if not skip_flag:
                            if CARGO:
                                # call = f"{args.cargo_bin}/cargo_ftio --server {args.cargo_server} -c {prediction['conf']} -p {prediction['probability']} -t {1/prediction['freq']}"
                                call = f"{args.cargo_bin}/cargo_ftio --server {args.cargo_server} --run"
                                os.system(call)

                            # to use maybe later
                            period = 1/prediction['freq'] if prediction['freq'] > 0 else 0
                            text = f"frequency: {prediction['freq']}\nperiod: {period} \nconfidence: {prediction['conf']}\nprobability: {prediction['probability']}\n"
                            CONSOLE.print("[bold green][Trigger][/][green]" + call +"\n"+text)
                        else:
                            CONSOLE.print("[bold green][Trigger][/][yellow] Skipping, new prediction is ready[/]\n")

                    else:
                        CONSOLE.print("[bold green][Trigger][/][yellow] Skipping, not in time[/]\n")

            time.sleep(0.01)
        except KeyboardInterrupt:
            exit()


def setup_cargo(tmp_args):
    if CARGO:
        #1. Perform stage in outside FTIO with cpp
        #2. Setup für Cargo Stage-out für cargo_ftio
        call = f"{tmp_args.cargo_bin}/cargo_ftio --server {tmp_args.cargo_server} --run"
        CONSOLE.print("\n[bold green][Init][/][green]" + call +"\n")
        os.system(call)

        # 3. tells cargo that for all next cargo_ftio calls use the cpp
        # input is relative from GekokFS
        call = f"{tmp_args.cargo_bin}/ccp --server {tmp_args.cargo_server} --input / --output {tmp_args.cargo_out} --if gekkofs --of parallel"
        CONSOLE.print("\n[bold green][Init][/][green]" + call + "\n")
        os.system(call)
        # 4. trigger with the thread
        # 5. Do a stage out outside FTIO with cargo_ftio --run


if __name__ == "__main__":
    main(sys.argv)