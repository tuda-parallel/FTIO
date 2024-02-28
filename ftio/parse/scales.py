"""Handels the importing of modules
"""
import json
import os
import datetime
import jsonlines
import pandas as pd
import numpy as np
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from ftio import __version__
from ftio.parse.simrun import Simrun
from ftio.parse.parse_recorder import ParseRecorder
from ftio.parse.parse_darshan import ParseDarshan
from ftio.parse.parse_msgpack import ParseMsgpack
from ftio.parse.parse_txt import ParseTxt
from ftio.parse.parse_custom import ParseCustom
from ftio.parse.args import parse_args


class Scales:
    """load the data. Supports single files (json, jsonl, darshan) or folders (+ recorder)
    """
    def __init__(self, argv):
        self.Print_info(argv[0])
        self.render = ""
        self.plot_mode = ""
        self.mode = ""
        self.ts = -1
        self.threaded = ""
        self.zoom = -1
        self.same_path = False
        self.names = []
        self.s = []

        # save call
        self.save_call(argv)

        # Parse arguments
        self.args = parse_args(argv)

        if isinstance(self.args.files, list):
            if len(self.args.files) <= 1:
                self.paths = ["."]
            else:
                self.paths = []
                for i in range(1, len(self.args.files)):
                    self.paths.append(str(self.args.files[i]))
        else:
            self.paths = [self.args.files]

        # data = []
        self.Check_Same_Path()
        console = Console()
        for path in self.paths:
            #! load folders
            # Recorder folder
            if "_text" in path[-5:]:
                console.print(f"\n[cyan]Loading Recorder folder({self.paths.index(path) + 1},{len(self.paths)}):[/] {path}")
                run = ParseRecorder(path).to_simrun(self.args)
                self.s.append(run)

            # Folder
            elif (os.path.isdir(path)):
                console.print(f"\n[cyan]Loading  folder({self.paths.index(path) + 1},{len(self.paths)}):[/] {path}")
                if path[-1] == "/":
                    path = path[:-1]

                for root, _, files in os.walk(path):
                    if "io_results" in root or "exported_images" in root:
                        console.print(f"[yellow]Skipping folder:  {root}[/]")
                        continue
                    if "scale.jsonl" in files:
                        console.print(f"[yellow]Skipping folder:  {root}/scale.jsonl[/]")
                        files.remove("scale.jsonl")
                    sorted_files = sorted(files, key=len)

                    for file in sorted_files:
                        if any(ext in file for ext in ['json','darshan','msgpack','txt']):
                            file_path = os.path.join(root, file)
                            # Limit the number of ranks to consider if self.limit is defined
                            try:
                                if self.args.limit > 0 and get_rank(file) >= self.args.limit:
                                    console.print(f"[yellow]Skipping file: {file}[/]")
                                    continue
                            except Exception as error:
                                console.print(f"[red]Something went wrong with the limit. Error is {error}[/]")
                            self.names.append(root[root.rfind("/") + 1 :])
                            console.print(f"[cyan]Current file:[/] {file}")
                            self.load_file(file_path, self.paths.index(path))
                    break  # no recusive walk

            # Compare Several files
            elif not self.same_path and ".json" in path[-6:]:
                self.names.append(path)
                console.print(f"[cyan]Current file:[/] {path}")
                self.load_file(path, self.paths.index(path))

            # Single file
            else:
                self.names.append(get_filename(path))
                console.print(f"[cyan]Current file:[/] {path}\n")
                self.load_file(path)

        # print("--------------------------------------------\n")
        self.n = len(self.s)
        if self.names:
            names = self.names
            self.names = []
            for i in names:
                if i not in self.names:
                    self.names.append(i)

    def load_file(self, file_path:str, file_index = 0) -> None:
        """Load file content into an Simrun object

        Args:
            file_path (str): filename + absolute path
        """
        check_open(file_path)
        if self.args.custom_file:
            run = ParseCustom(file_path).to_simrun(self.args, file_index)
        elif ".json" in file_path[-5:]:
            with open(file_path,"rt") as file:
                data = json.load(file)
            run = Simrun(data, "json", file_path, self.args, file_index)
        elif ".jsonl" in file_path[-6:]:
            with jsonlines.open(file_path, "r") as jsonl_f:
                data = [obj for obj in jsonl_f]
            run = Simrun(data, "jsonl", file_path, self.args, file_index)
        elif "darshan" in file_path[-10:]:
            run = ParseDarshan(file_path).to_simrun(self.args, file_index)
        elif "msgpack" in file_path[-10:]:
            run = ParseMsgpack(file_path).to_simrun(self.args, file_index)
        elif "txt" in file_path[-10:]:
            run = ParseTxt(file_path).to_simrun(self.args, file_index)
        self.s.append(run)

    def save_call(self, argv):
        """save the call as a hidden file
        """
        self.call = ""
        for i in argv:
            self.call = self.call + " " + i
        f = open("%s/.call.txt" % (os.getcwd()), "a")
        f.write(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            + " :"
            + self.call
            + "\n\n"
        )
        f.close()

    def Print_info(self, text:str)-> None:
        name = text[text.rfind("/") + 1 : ].capitalize()
        console = Console()
        title = Panel(Text(name, justify="center"), style="bold white on cyan", border_style="white", title_align="left")
        text = "\n[cyan]Author:[/]  Ahmad Tarraf\n"
        text += f"[cyan]Date:[/]    {str(datetime.date.today())}\n"
        text += f"[cyan]Version:[/]  {__version__}\n"
        text += "[cyan]License:[/]  BSD\n"
        # console.print(Panel(Group(title,text), style="white", border_style='blue'))
        console.print(title)
        console.print(text)

    def Check_Same_Path(self):
        if len(self.paths) > 1:
            self.same_path = True
            same_path = ""
            for i in self.paths:
                if self.paths.index(i) == 0:
                    same_path = i[: i.rfind("/")]
                else:
                    if same_path != i[: i.rfind("/")]:
                        self.same_path = False
                        break
        else:
            self.same_path = True

    



    #! ----------------------- Pandas dataset functions ------------------------------
    # **********************************************************************
    # *                       1. get_data
    # **********************************************************************
    def get_data(self):
        self.df_rst = self.get_data_io("read_sync")
        self.df_wst = self.get_data_io("write_sync")
        self.df_rat = self.get_data_io("read_async_t")
        self.df_rab = self.get_data_io("read_async_b")
        self.df_wat = self.get_data_io("write_async_t")
        self.df_wab = self.get_data_io("write_async_b")
        self.df_time = self.get_data_time("io_time")

        # df = pd.concat([df,self.get_data_core('write_async_b')])

    # **********************************************************************
    # *                       2. get_data_io
    # **********************************************************************
    def get_data_io(self, io_mode="read_sync"):
        """Extract data from the file(s) and gathers in dataframes. 
        The fields name are store in "name_[level]" and their values are stored 
        in "data_[level]". There are 4 levels provided:
        (1) Application level (overlap or rank matrics): [..]_rank_ovr
        (2) rank level (sum/average of I/O requests): [..]_rank
        (3) high precesion rank level (overlap of I/O requests): [..]_ind_ovr
        (4) I/O request level (lowest level): [..]_rank_over

        if the 'ind' flag is not provieded, level (3) and (4) are skipped as they are 
        expensive to calculate. 
        

        Args:
            io_mode (str, optional): Can be read or write and 
            sync or async (required [b] or actual [t]). Supported modes are:
            "read_sync", "write_sync", "read_async_t", "read_async_b", "write_async_t", 
            and "write_async_b".Defaults to "read_sync".

        Returns:
            tuple[pd.DataFrame,pd.DataFrame, 
            pd.DataFrame, pd.DataFrame, pd.DataFrame,]: Five dataframes are 
            returned. The first one contains metrics like total bytes transfered, number 
            of phases, etc.. The next 4 dataframes contain the I/O data at the 4 
            levels explained above
        """
        name = ""
        data_metrics = np.array([])
        for i in range(0, self.n):
            value = getattr(self.s[i], io_mode)
            data = value.get_data()
            if i == 0:
                name = data[0]
                name_rank_ovr = data[2]
                name_rank = data[4]
                name_ind_ovr = data[6]
                name_ind = data[8]
                data_metrics = np.array(data[1])
                data_rank_ovr = np.array(data[3])
                data_rank = np.array(data[5])
                data_ind_ovr = np.array(data[7])
                data_ind = np.array(data[9])

            else:
                data_metrics = np.vstack((data_metrics, data[1]))
                data_rank_ovr = np.concatenate((data_rank_ovr, data[3]), axis=1)
                data_rank = np.concatenate((data_rank, data[5]), axis=1)
                data_ind_ovr = np.concatenate((data_ind_ovr, data[7]), axis=1)
                data_ind = np.concatenate((data_ind, data[9]), axis=1)
            # data.append(d0)
        # check if there is data
        if data_metrics.size == 0:
            raise RuntimeError(f"The mode {self.args.mode} contains no values\nChange the mode by using the -m argument.")
        
        df0 = pd.DataFrame(data_metrics, columns=name)
        df0 = df0.sort_values(by=["number_of_ranks"])
        df1 = pd.DataFrame(data_rank_ovr.transpose(), columns=name_rank_ovr)
        df1 = df1.astype({"number_of_ranks": "int"})
        df2 = pd.DataFrame(data_rank.transpose(), columns=name_rank)
        df3 = pd.DataFrame(data_ind_ovr.transpose(), columns=name_ind_ovr)
        df4 = pd.DataFrame(data_ind.transpose(), columns=name_ind)

        return df0, df1, df2, df3, df4

    # **********************************************************************
    # *                       3. get_data_time
    # **********************************************************************
    def get_data_time(self, io_mode="io_time"):
        data = []
        name = ""
        for i in range(0, self.n):
            value = getattr(self.s[i], io_mode)
            if i == 0:
                name, d0 = value.get_data()  # Time function
            else:
                _, d0 = value.get_data()

            data.append(d0)
        df0 = pd.DataFrame(data, columns=name)
        df0 = df0.sort_values(by=["number_of_ranks"])
        return df0


def check_open(file:str) -> None:
    """Checks that the file is accessible 

    Args:
        file (str): filename
    """
    if os.path.isfile(file):
        pass
    else:
        console = Console()
        console.print(f"[red]--- Error  --- [/]\n"
            f"[red]-> Could not open file [b]{file}[/b]. \n[/]"
            f"[yellow]Make sure [b]{file}[/b] exists in [b]{os.getcwd()}[/b]. \n\n[/]"
        )
        exit()


def get_rank(name:str) -> int:
    """Get the number of ranks from the name of the file

    Args:
        name (str): name of file

    Returns:
        int: number of ranks
    """
    if isinstance(name, int):
        return name
    else:
        start = name.rfind("/")
        end = max(
            name.rfind(".json"),
            name.rfind(".darshan"),
            name.rfind(".msgpack")
        )
        rank = name[start + 1 : end]
        strs = ["_", "-", " "]
        if any(x in rank for x in strs):
            for x in strs:
                if x in rank:
                    end = rank.rfind(x)
                    rank = rank[:end]
        return int(rank)


def get_filename(path:str) -> str:
    """Reutrns filename from absolute path

    Args:
        path (str): absolute path to file (including name)

    Returns:
        str: filename
    """
    tmp = path.rfind("/")
    out = path[tmp + 1 :] if tmp > 0 else path
    return out