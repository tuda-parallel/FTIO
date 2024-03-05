"""Parse zmq message contaiting three fields: 
the bandwidth, the start time, and the end time.
"""
from ftio.parse.simrun import Simrun
from ftio.parse.zmq_reader import extract

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
        dataframe, ranks = extract(self.msg, args)

        return Simrun(dataframe,'txt',str(ranks), args, index)
