"""Parse zmq message containing three fields:
the bandwidth, the start time, and the end time.
"""

import zmq
from ftio.parse.simrun import Simrun
from ftio.parse.zmq_reader import extract
from ftio.parse.msgpack_reader import extract_data
from ftio.freq.helper import MyConsole


class ParseZmq:
    """class to parse zmq file"""

    def __init__(self, msgs):
        self.msgs = msgs

    def to_simrun(self, args, index: int = 0):
        """Convert to Simrun class
        Args:
            ars (argparse): command line arguments
            index: file index in case several files are passed
        Returns:
            Simrun: Simrun object
        """
        # For FTIO not PREDICTOR
        if self.msgs is None:
            self.msgs = get_msgs_zmq(args)

        if "direct" in args.zmq_source:
            for msg in self.msgs:
                dataframe, ranks = extract(msg, args)
            return Simrun(dataframe, "txt", str(ranks), args, index)
        elif "tmio" in args.zmq_source.lower():
            data = extract_data(self.msgs[0], [])
            return Simrun(data, "msgpack", "0", args, index)
        else:
            pass


# For FTIO only
def get_msgs_zmq(args) -> list[str]:
    CONSOLE = MyConsole()
    CONSOLE.set(True)
    context = zmq.Context()
    socket = context.socket(socket_type=zmq.PULL)

    # socket.bind('tcp://*:5555')
    socket.bind(f"tcp://{args.zmq_address}:{args.zmq_port}")

    # can be extended to listen to multiple sockets
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    msgs = []
    ranks = 0
    socks = dict(poller.poll(1000))
    while True:
        while socks:
            if socks.get(socket) == zmq.POLLIN:
                msg = socket.recv(zmq.NOBLOCK)
                msgs.append(msg)
                ranks += 1
            socks = dict(poller.poll(1000))

        if not msgs:
            CONSOLE.print("[red]No messages[/]")
            continue
        else:
            CONSOLE.print("[green]All message received[/]")
            break

    return msgs
