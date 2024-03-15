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
        "req_size": [],
        "total_bytes": 0,
        "total_iops": 0,
    }

    # 1) overlap for rank level metrics
    for file_or_msg in files_or_msgs:
        data_rank, ext = parse(file_or_msg, data_rank)

    # 2) Scale if JSON or MsgPack
        scale = [1, 1, 1]
        if "JSON" in ext.upper():
            scale = [1.07 * 1e6, 1e-3, 1e-3]
        elif "MSG" in ext.upper():
            scale = [1, 1e-6, 1e-6]
            
        b_rank   = np.array(data_rank["avg_thruput_mib"]) * scale[0]
        t_rank_s = np.array(data_rank["start_t_micro"]) * scale[1]
        t_rank_e = np.array(data_rank["end_t_micro"]) * scale[2]

        # 3) app level bandwidth
        b, t = overlap(b_rank, t_rank_s, t_rank_e)
        
    # 4) Extend for ZMQ
    if "ZMQ" in ext.upper():
        # extend data
        b_app.extend(list(b))
        t_app.extend((t))
        t = np.array(list(t_app))
        b = np.array(list(b_app))
    else:
        t = np.array(list(b))
        b = np.array(list(t))

    # 5) plot to check:
    if any(x in args.engine for x in ["mat", "plot"]):
        fig = go.Figure()
        unit, order = set_unit(b)
        fig.add_trace(go.Scatter(x=t, y=b * order, name="App Bandwidth",line={"shape": "hv"}))
        fig.update_layout(xaxis_title="Time (s)", yaxis_title=f"Bandwidth ({unit})")
        fig = format_plot(fig)
        fig.show()

    # 6) set up data
    data = {
        "time": t,
        "bandwidth": b,
        "total_bytes": data_rank["total_bytes"],
        "ranks": ranks,
    }

    # 7) perform prediction
    prediction, dfs = core([data], args)

    # 8) plot and print info
    display_prediction(["./ftio"], prediction)
    convert_and_plot(data, dfs, args)

    return prediction, args


if __name__ == "__main__":
    # absolute path to search all text files_or_msgs inside a specific folder
    # path=r'/d/github/FTIO/examples/API/gekkoFs/JSON/*.json'
    path = r"/d/github/FTIO/examples/API/gekkoFs/MSGPACK/write*.msgpack"
    matched_files_or_msgs = glob.glob(path)
    run(matched_files_or_msgs)
