"""Parse zmq message containing three fields: 
the bandwidth, the start time, and the end time.
"""
import zmq
from ftio.parse.simrun import Simrun
from ftio.parse.zmq_reader import extract
from ftio.parse.msgpack_reader import extract_data

class ParseZmq:
    """class to parse zmq file
    """
    def __init__(self, msg):
        self.msg = msg

    def to_simrun(self, args, index:int = 0):
        """Convert to Simrun class
        Args:
            ars (argparse): command line arguments
            index: file index in case several files are passed
        Returns:
            Simrun: Simrun object
        """
        if len(self.msg) == 0:
            context = zmq.Context()
            socket = context.socket(socket_type=zmq.PULL)
            # socket.connect(args.zmq_port)
            socket.bind(args.zmq_port)
            print("waiting for msg")
            self.msg = socket.recv()
            print("msg received")

        if isinstance(self.msg,Simrun):
            pass #TODO: add Simrun extend and append TMIO in predictor_zmq
        elif "direct" in args.zmq_source:
            dataframe, ranks = extract(self.msg, args)
            return Simrun(dataframe,'txt',str(ranks), args, index)
        elif "tmio" in args.zmq_source.lower():
            data = extract_data(self.msg, [])
            return Simrun(data,'msgpack', '0', args, index)
        else:
            pass
