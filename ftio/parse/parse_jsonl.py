from ftio.parse.simrun import Simrun
import jsonlines


class ParseJsonl:
    def __init__(self, path):
        self.path = path
        if self.path[-1] == "/":
            self.path = self.path[:-1]

    def to_simrun(self, args, index=0):
        """Convert to Simrun class
        Args:
            ars (argparse): command line arguments
            index: file index in case several files are passed
        Returns:
            Simrun: Simrun object
        """
        file = self.path
        with jsonlines.open(file, "r") as jsonl_f:
            data = [obj for obj in jsonl_f]

        return Simrun(data, "jsonl", file, args, index)
