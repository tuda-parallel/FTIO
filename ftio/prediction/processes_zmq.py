"""Performs prediction with Pools (ProcessPoolExecutor) and a callback mechanism"""
from __future__ import annotations
import zmq
from ftio.prediction.async_process import join_procs
from ftio.prediction.processes import prediction_process
from ftio.prediction.helper import print_data, export_extrap
from ftio.prediction.async_process import handle_in_process
from ftio.parse.args import parse_args
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()
CONSOLE.set(True)

def predictor_with_processes_zmq(
    data, queue, count, hits, start_time, aggregated_bytes, args, b_app, t_app
)-> None:
    """performs prediction in ProcessPoolExecuter. FTIO is a submitted future and probability is calculated as a callback

    Args:   
        filename (str): name of file
        data (Manager().list): List of dicts with all predictions so far
        queue (Manager().Queue): queue for FTIO data
        count (Manager().Value): number of prediction
        hits (Manager().Value): hits indicating how often a dominant frequency was found
        start_time (Manager().Value): start time window for ftio
        aggregated_bytes (Manager().Value): total bytes transferred so far
        args (list[str]): additional arguments passed to ftio
    """
    procs = []
    context = zmq.Context()
    socket = context.socket(socket_type=zmq.PULL)
    tmp_args = parse_args(args)
    socket.bind(f'tcp://{tmp_args.zmq_address}:{tmp_args.zmq_port}')
    
    # can be extended to listen to multiple sockets
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    
    if '-zmq' not in args:
        args.extend(['--zmq'])
    
    # Loop and predict if changes occur
    try:
        while True:
            if procs:
                procs = join_procs(procs)
            #1) just a single msg
            # msg = socket.recv(zmq.NOBLOCK)  

            #2) Loop and accept messages from both channels, acting accordingly
            # if socks:
            #     if socks.get(socket) == zmq.POLLIN:
            #         print(f"got message ",{socket.recv(zmq.NOBLOCK)})
            # else:
            #     print("No message received")
            #     continue
            
            #3) Loop and accept messages from both channels, acting accordingly
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
            CONSOLE.print(f"[green]All message received from {ranks} ranks[/]")

            # launch prediction_process
            # TODO: append b_app and t_app like predictor_gekko_zmq use the flag --zmq to indicate this
            # put all in msgs and call it zmq_data
            procs.append(
                handle_in_process(
                    prediction_process,
                    args=(data, queue, count, hits, start_time, aggregated_bytes, args, msgs)
                )
            )
    except KeyboardInterrupt:
        print_data(data)
        export_extrap(data)
        print('-- done -- ')


