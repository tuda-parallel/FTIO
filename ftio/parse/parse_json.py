import json
from ftio.parse.simrun import Simrun
from ftio.freq.helper import MyConsole
from ftio.parse.helper import match_mode, detect_source

class ParseJson:
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
        with open(file, "rt") as current_file:
            data = json.load(current_file)

        source = detect_source(data, args)
        if 'tmio' in source:
            pass
        else:
            data, args = self.adjust(data, args)

        return Simrun(data, "json", file, args, index)


    def adjust(self, data:dict, args):
        # check for mode
        fields = list(data.keys())
        if any( x in fields for x in ['read_sync', 'read_async', 'write_sync', 'write_async']):
            args.source = 'custom'
            if args.mode and match_mode(args.mode) in data:
                self.add_missing_fields(data,match_mode(args.mode))
            else:
                CONSOLE = MyConsole()
                CONSOLE.info(f"[yellow]Warning: [/] Mode [yellow]{args.mode}[/] does not exist in trace")
                for x in ['read_sync', 'read_async', 'read_async', 'write_async']:
                    if x in fields:
                        args.mode = x
                        CONSOLE.info(f"[yellow]Warning: [/] Adjusting mode to [yellow]{args.mode}[/]")
                        self.add_missing_fields(data,match_mode(args.mode))
                        break

        elif  'bandwidth' in data:
            data = {"read_sync":{
                    "total_bytes": 0,
                    "number_of_ranks": 0 ,
                    "bandwidth": data['bandwidth']
                    }}
            args.mode = "read_sync"
            args.source = 'custom'
        elif "b_rank" in data:
            data = {"read_sync":{
                    "total_bytes": 0,
                    "number_of_ranks": 0 ,
                    "bandwidth": 
                        {
                        "b_rank_avr": data["b_rank_avr"],
                        "t_rank_s":  data["t_rank_s"],
                        "t_rank_e": data["t_rank_e"]
                    }
                    }}
            args.mode = "read_sync"
            args.source = 'custom'
        elif "b_overlap" in data:
            data = {"read_sync":{
                    "total_bytes": 0,
                    "number_of_ranks": 0 ,
                    "bandwidth": 
                        {
                        "b_overlap_avr": data["b_overlap"],
                        "t_overlap":  data["t_overlap"],
                    }
                    }}
            args.mode = "read_sync"
            args.source = 'custom'
        else:
            raise ValueError("Mode not found")

        return data, args

    def add_missing_fields(self,data,mode):
        fields = ["total_bytes", "number_of_ranks"]
        for field in fields:
            if field not in data[mode]:
                data[mode][field] = 0

