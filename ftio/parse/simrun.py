from __future__ import annotations
import statistics as st
from ftio.parse.sample import Sample
from ftio.parse.time_io import Time
from ftio.parse.percent import Percent
import re 
class Simrun:
    """Stores the result from a single simulation including the:
    1. read sync
    2. read async
    3. write sync
    4. write async
    5. I/O time (if avilable)
    6. I/O percent (if avilable)
    """
    def __init__(self, data, ext: str,  name: str, args, file_index: int = 0):
        """create Simrun objct

        Args:
            data (array): contains data from simulation
            ext (str): 'json', 'jsonl', 'recorder', 'darshan', 'msgpack', or 'txt'
            name (str): name of simulation (e.g., 192.json)
            args (argparse): comand line arguments
            file_index (int, optional): file index, in case several files have the same name
        """
        self.name       = name
        self.ranks      = self.get_rank(ext)
        mode            = args.mode if args.mode else ''
        args.file_index = file_index

        #! list = jsonlines
        if isinstance(data,list):
            #! jsonlines need to be converted to a dict
            # if 'Time' in data[-1]:
            if 'jsonl' in ext or 'msgpack' in ext:
                if mode and mode in ['sync_read', 'sync_write', 'async_read', 'async_write']:
                    self.reset(args)
                    self.assign(data, args, mode,'jsonl')
                else:
                    self.read_sync     = self.merge_parts(data,'read_sync', args)
                    self.read_async_t  = self.merge_parts(data,'read_async_t', args)
                    self.read_async_b  = self.merge_parts(data,'read_async_b', args)
                    self.write_async_t = self.merge_parts(data,'write_async_t', args)
                    self.write_async_b = self.merge_parts(data,'write_async_b', args)
                    self.write_sync    = self.merge_parts(data,'write_sync', args)
                    if any('io_time' in d for d in data):
                        self.io_time       = self.merge_parts(data,'io_time',args)
                        self.io_percent    = Percent(self.io_time)
            else:
                raise ValueError('Data format empty or not supported')

        #! Darshan files or recorder files
        elif 'darshan' in ext or 'recorder' in ext:
            self.reset(args)
            self.read_sync         = Sample(data['read_sync'],'read_sync',args)
            self.write_sync        = Sample(data['write_sync'],'write_sync',args)
            self.io_time           = Time(data['io_time'],self.ranks,args)

        elif 'txt' in ext:
            self.reset(args)
            mymode = self.getmode(mode)
            setattr(self,mymode,Sample(data[mymode],mymode,args))
            self.io_time           = Time(data['io_time'],self.ranks,args)

        #! json files
        else:
            #! for dft to make it faster
            if mode and mode in ['sync_read', 'sync_write', 'async_read', 'async_write']:
                self.reset(args)
                self.assign(data,args,mode)
                return
            #! standard json files
            self.read_sync     = Sample(data['read_sync'],    'read_sync',args)
            self.read_async_t  = Sample(data['read_async_t'], 'read_async_t',args)
            self.read_async_b  = Sample(data['read_async_b'], 'read_async_b',args)
            self.write_async_t = Sample(data['write_async_t'],'write_async_t',args)
            self.write_async_b = Sample(data['write_async_b'],'write_async_b',args)
            self.write_sync    = Sample(data['write_sync'],   'write_sync',args)
            if 'io_time' in data:
                self.io_time       = Time(data['io_time'],self.ranks,args)
                self.io_percent    = Percent(self.io_time)


#---------------------------------------------------------------------------------------------------
#?=======================
#? helper functions
#?=======================
    def assign(self,data, args, mode, file_format = 'json'):
        """assigns a single mode instead of parsing all data

        Args:
            data (array): sim data
            args (argparse): command line arguments
            mode (str): mode to assign
            format (str, optional): json or jsonl. Defaults to 'json'.
        """
        if 'jsonl' in file_format:
            if 'sync_read' == mode:
                self.read_sync     = self.merge_parts(data,'read_sync',args)
            elif 'async_read' == mode:
                self.read_async_t  = self.merge_parts(data,'read_async_t',args)
                self.read_async_b  = self.merge_parts(data,'read_async_b',args)
            elif 'sync_write' == mode:
                self.write_sync     = self.merge_parts(data,'write_sync',args)
            elif 'async_write' == mode:
                self.write_async_t  = self.merge_parts(data,'write_async_t',args)
                self.write_async_b  = self.merge_parts(data,'write_async_b',args)
            else:
                pass

            if any('io_time' in d for d in data):
                self.io_time       = self.merge_parts(data,'io_time',args)
                self.io_percent    = Percent(self.io_time)

        else:
            if 'sync_read' == mode:
                self.read_sync     = Sample(data['read_sync'],    'read_sync',args)
            elif 'async_read' == mode:
                self.read_async_t  = Sample(data['read_async_t'], 'read_async_t',args)
            elif 'async_write' == mode:
                self.write_async_t = Sample(data['write_async_t'],'write_async_t',args)
            elif 'sync_write' == mode:
                self.write_sync    = Sample(data['write_sync'],   'write_sync',args)


    def reset(self, args):
        """sets all fields to empty. This is usually followed by a assign call

        Args:
            args (argparse): command line arguments
        """
        self.read_sync     = Sample({'bandwidth':[]},'read_sync', args)
        self.read_async_t  = Sample({'bandwidth':[]},'read_async_t', args)
        self.read_async_b  = Sample({'bandwidth':[]},'read_async_b', args)
        self.write_async_t = Sample({'bandwidth':[]},'write_async_t', args)
        self.write_async_b = Sample({'bandwidth':[]},'write_async_b', args)
        self.write_sync    = Sample({'bandwidth':[]},'write_sync', args)
        self.io_time       = Time({}, self.ranks, args)


    def get_rank(self,ext:str) -> int:
        """Get rank name from exetension

        Args:
            ext (str): extension type

        Returns:
            int: number of ranks that did I/O
        """
        out = -1
        if isinstance(self.name,int):
            out = self.name
        elif isinstance(self.name,str) and '.' not in self.name and '/' not in self.name:
            out = int(self.name)
        else:
            try:
                name_s = self.name.rfind("/")
                if name_s < 0:
                    name_s = self.name.rfind("\\") # for windows
                name_e = self.name.rfind(f".{ext}")
                rank = self.name[name_s+1:name_e]
                strs = ["_","-"," "]
                if any(x in rank for x in strs):
                    for x in strs:
                        if x in rank:
                            name_e = rank.rfind(x)
                            rank = rank[:name_e]
                out = int(rank)
            except ValueError:
                rank = re.findall(r'\d+', "hello 42 I'm a 32 string 30")
                out = int(rank[-1])
        return out


    def print_rank(self,file):
        """print rank maped to POINTS. This is used for 
        Extra-P with the text file format.

        Args:
            file (fileptr): file pointer
        """
        file.write(f"POINTS ( {self.ranks:i} )\n")


    def merge_parts(self,data,mode,args):
        """merge jsonl parts to a single simulation

        Args:
            data (2d array): array fo data elelements
            mode (str): mode to merge
            args (argparse): command line arguments

        Returns:
            io_sampe object: iosample of the whole simulation
        """
        data_array     = [item[mode] for item in data if mode in item]
        out = []
        if len(data_array) <= 1:
            if "time" in mode:
                out = Time(data_array[0],self.ranks,args)
            else:
                out = Sample(data_array[0],mode,args)
        else:
            data_array = self.merge_fields(data_array)
            if "time" in mode:
                out = Time(data_array,self.ranks,args)
            else:
                out = Sample(data_array,mode,args)
        return out


    def merge_fields(self,data_array, keys: list[str] = []) -> dict:
        """Merges the metrics field from different files. For example,
        JsonlLines file constantly append new data. To merge the previous 
        metrics with the new one, this function itterates over the fields 
        and merges them.

        Args:
            data_array (dataframe): Metrics
            keys (list[str], optional): _description_. Defaults to list[str].

        Returns:
            dict: merge fields in stored in a dict variable
        """
        if not keys:
            keys = [k for k in data_array[0].keys()]

        my_dict = {}
        for field in keys:
            # print(f)
            if isinstance(data_array[0][field],dict):
                data_array2  = [x[field] for x in data_array if field in x]
                my_dict[field] = self.merge_fields(data_array2,[k for k in data_array2[0].keys()])
            else:
                if isinstance(data_array[0][field],list):
                    my_dict[field] = []
                    for i,_ in enumerate(data_array):
                        my_dict[field].extend(data_array[i][field])
                else:
                    if any([x in field for x in ['total','_t_']]):
                        my_dict[field] = sum(x[field] for x in data_array)
                    elif any([x in field for x in ['max','number']]):
                        my_dict[field] = max(x[field] for x in data_array)
                    elif 'min' in field:
                        my_dict[field] = min(x[field] for x in data_array)
                    elif 'arithmetic_mean' in field:
                        my_dict[field] = st.mean(x[field] for x in data_array)

        return my_dict

    def getmode(self, mode:str) -> str:
        if "w" in mode:
            out = "write"
        else:
            out = "read"
            
        if "async" in mode:
            out = out + "_async_t"
        else:
            out = out + "_sync"

        return out 