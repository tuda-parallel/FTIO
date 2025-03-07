"""Performs prediction with Pools (ProcessPoolExecutor) and a callback mechanism"""
from __future__ import annotations
import zmq
import subprocess
from ftio.multiprocessing.async_process import join_procs, handle_in_process
from ftio.prediction.processes import prediction_process
from ftio.prediction.helper import print_data, export_extrap
from ftio.parse.args import parse_args
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()
CONSOLE.set(True)

def predictor_with_processes_zmq(
    shard_resources, args, 
)-> None:
    """performs prediction in ProcessPoolExecuter. FTIO is a submitted future and probability is calculated as a callback

    Args:   
        shared_resources (SharedResources): shared resources among processes
        args (list[str]): additional arguments passed to ftio
    """
    procs = []
    context = zmq.Context()
    socket = context.socket(socket_type=zmq.PULL)
    #parse arguments
    tmp_args = parse_args(args)
    addr = tmp_args.zmq_address
    port = tmp_args.zmq_port

    # bind the socket
    socket = bind_socket(addr,port)
    # can be extended to listen to multiple sockets
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    
    if '-zmq' not in args:
        args.extend(['--zmq'])
    
    # Loop and predict if changes occur
    try:
        with CONSOLE.status("[green] started\n",spinner="arrow3") as status:
            while True:
                # join procs
                procs = join_procs(procs)
                # get messages
                msgs, ranks = receive_messages(socket, poller)

                if not msgs:
                    CONSOLE.print("[red]No messages[/]")
                    continue
                CONSOLE.print(f"[cyan]Got message from {ranks}:[/]")
                status.update("")

                # launch prediction 
                # TODO: append b_app and t_app 
                procs.append(
                    handle_in_process(
                        prediction_process,
                        args=(shard_resources, args, msgs)
                    )
                )
    except KeyboardInterrupt:
        print_data(shard_resources.data)
        export_extrap(shard_resources.data)
        print('-- done -- ')



def bind_socket(addr, port):
    """Bind the ZMQ socket, retrying with a corrected IP if necessary."""
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    try:
        socket.bind(f"tcp://{addr}:{port}")
    except zmq.error.ZMQError as e:
        CONSOLE.print(f"[yellow]Error encountered:\n{e}[/]")
        CONSOLE.print("[yellow]Wrong IP address. Attempting to correct...[/]")
        addr = str(subprocess.check_output("ip addr | grep 'inet 10' | awk  '{print $2}'", shell=True))
        end   = addr.rfind("/")
        start = addr.find("'")
        addr = addr[start+1:end]
        CONSOLE.print("[bold green]Corrected IP address:[/]", addr)
        socket.bind(f"tcp://{addr}:{port}")

    CONSOLE.print(f"[green]FTIO is running on: {addr}:{port}[/]")

    return socket



def receive_messages(socket, poller):
    """Polls for and receives messages from the socket, returning a list of messages and count."""
    msgs = []
    ranks = 0
    # start = time.time()
    socks = dict(poller.poll(1000))
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
    while socks: 
        if socks.get(socket) == zmq.POLLIN:
            msgs.append(socket.recv(zmq.NOBLOCK))
            # CONSOLE.print(f"[cyan]Got message {ranks}:[/] {msg}")
            ranks += 1
        # if time.time() - start > 0.5:
        #     break
        socks = dict(poller.poll(1000))
    
    return msgs, ranks