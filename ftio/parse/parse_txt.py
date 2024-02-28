"""Parse text file contaiting three fields: 
the bandwidth, the start time, and the end time.
"""
from ftio.parse.simrun import Simrun
from ftio.parse.txt_reader import extract

class ParseTxt:
    """class to parse txt file
    """
    def __init__(self, path):
        self.path = path
        if self.path[-1] == "/":
            self.path = self.path[:-1]

    def to_simrun(self, args, index:int = 0):
        """Convert to Simrun class
        Args:
            ars (argparse): command line arguments
            index: file index in case several files are passed
        Returns:
            Simrun: Simrun object
        """
        dataframe, ranks = extract(self.path, args)

        return Simrun(dataframe,'txt',str(ranks), args, index)


