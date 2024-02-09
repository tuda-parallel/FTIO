from ftio.parse.simrun import Simrun
from ftio.parse.msgpack_reader import extract

class ParseMsgpack:
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
        file = self.path
        data = extract(file)

        return Simrun(data,'msgpack', file, args, index)