from ftio.parse.simrun import Simrun
from ftio.parse.darshan_reader import extract

class ParseDarshan:
    """class to parse Darshan files
    """
    def __init__(self, path):
        self.path = path
        if self.path[-1] == "/":
            self.path = self.path[:-1]

    def to_simrun(self, args, index = 0):
        """Convert to Simrun class
        Args:
            ars (argparse): command line arguments
            index: file index in case several files are passed
        Returns:
            Simrun: Simrun object
        """
        dataframe, ranks = extract(self.path, args)

        return Simrun(dataframe,'darshan',str(ranks), args, index)
