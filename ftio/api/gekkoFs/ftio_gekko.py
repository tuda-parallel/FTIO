import numpy as np
import glob
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.freq.freq_plot_core import convert_and_plot
from ftio.parse.bandwidth import overlap
from ftio.api.gekkoFs.parse_gekko import parse
import plotly.graph_objects as go
from ftio.freq.helper import format_plot
from ftio.plot.units import set_unit
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()
CONSOLE.set(True)

def run(files_or_msgs: list, argv:list[str]=["-e", "plotly", "-f", "100"], b_app = [], t_app = []):  # "0.01"] ):
    """Executes ftio on list of files_or_msgs.

    Args:
        files_or_msgs (list): _description_
        argv: command line arguments from ftio
        data_rank
    """

    # parse args
    args = parse_args(argv, "ftio")
    ranks = len(files_or_msgs)

    # Set up data
    data_rank = {
        "avg_thruput_mib": [],
        "end_t_micro": [],
        "start_t_micro": [],
        "hostname": "",
        "pid": 0,
        "io_type":"",
        "req_size": [],
        "total_bytes": 0,
        "total_iops": 0,
        "flush_t": 0, 
    }

    # 1) overlap for rank level metrics
    for file_or_msg in files_or_msgs:
        data_rank, ext = parse(file_or_msg, data_rank, io_type = args.mode[0])

    # 2) exit if no new data
    if not data_rank["avg_thruput_mib"]:
        CONSOLE.print("[red]Terminating prediction ... [/]")
        exit(0)
    
    # 3) Scale if JSON or MsgPack
    scale = [1, 1, 1]
    if "JSON" in ext.upper():
        scale = [1.07 * 1e6, 1e-3, 1e-3]
    elif any(x in ext.upper() for x in ["MSG", "ZMQ"]): 
        scale = [1, 1e-6, 1e-6]
        
    b_rank   = np.array(data_rank["avg_thruput_mib"]) * scale[0]
    t_rank_s = np.array(data_rank["start_t_micro"]) * scale[1]
    t_rank_e = np.array(data_rank["end_t_micro"]) * scale[2]
    if "flush_t" in data_rank:
        data_rank["flush_t"] = data_rank["flush_t"]* scale[2]

    # 4) app level bandwidth
    b, t = overlap(b_rank, t_rank_s, t_rank_e)
        
    # 5) Extend for ZMQ
    if "ZMQ" in ext.upper(): # or use args.zmq
        # extend data
        b_app.extend(b)
        t_app.extend(t)
        t = np.array(t_app[:])
        b = np.array(b_app[:])
    else:
        t = np.array(list(b))
        b = np.array(list(t))

    # 6) plot to check:
    if any(x in args.engine for x in ["mat", "plot"]):
        fig = go.Figure()
        unit, order = set_unit(b)
        fig.add_trace(go.Scatter(x=t, y=b * order, name="App Bandwidth",line={"shape": "hv"}))
        fig.update_layout(xaxis_title="Time (s)", yaxis_title=f"Bandwidth ({unit})")
        fig = format_plot(fig)
        fig.show()

    # 7) set up data
    data = {
        "time": t,
        "bandwidth": b,
        "total_bytes": data_rank["total_bytes"],
        "ranks": ranks,
    }

    # 8) perform prediction
    prediction, dfs = core([data], args)

    # 9) plot and print info
    display_prediction("ftio", prediction)
    convert_and_plot(data, dfs, args)

    return prediction, args, data_rank["flush_t"]


if __name__ == "__main__":
    # absolute path to search all text files_or_msgs inside a specific folder
    # path=r'/d/github/FTIO/examples/API/gekkoFs/JSON/*.json'
    path = r"/d/github/FTIO/examples/API/gekkoFs/MSGPACK/write*.msgpack"
    matched_files_or_msgs = glob.glob(path)
    run(matched_files_or_msgs)
