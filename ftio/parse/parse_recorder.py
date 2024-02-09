from ftio.parse.simrun import Simrun
from ftio.parse.recorder_reader import extract

class ParseRecorder:
    
    def __init__(self, path):
        self.path = path
        if self.path[-1] == "/":
            self.path = self.path[:-1]

    def to_simrun(self, args):
        """Convert to Simrun class
        Args:
            ts (double): [optional] desired start time
        Returns:
            Simrun: Simrun object
        """
        data, ranks = extract(self.path, args)

        return Simrun(data, 'recorder', str(ranks), args)
