# import os
import argparse
import glob

import numpy as np
import plotly.graph_objects as go

from ftio.freq.prediction import Prediction
from ftio.api.gekkoFs.parse_gekko import parse
from ftio.cli.ftio_core import core
from ftio.freq.helper import MyConsole
from ftio.multiprocessing.async_process import handle_in_process
from ftio.parse.args import parse_args
from ftio.parse.bandwidth import overlap, overlap_two_series
from ftio.plot.helper import format_plot
from ftio.plot.units import set_unit
from ftio.prediction.helper import dump_json
from ftio.processing.print_output import display_prediction

CONSOLE = MyConsole()
CONSOLE.set(True)


def run(
    files_or_msgs: list, argv=["-e", "plotly", "-f", "100"], b_app=[], t_app=[]
) -> tuple[Prediction, argparse.Namespace, float]:  # "0.01"] ):
    """Executes ftio on a list of files_or_msgs.

    Args:
        files_or_msgs (list): list with msgpack msg or json files
        argv: command line arguments for ftio
        b_app: app level bandwidth
        t_app: app level timestamps
    """

    # parse args
    args = parse_args(argv, "ftio")
    ranks = len(files_or_msgs)

    # Set up data
    data_rank = {
        "avg_throughput": [],
        "t_end": [],
        "t_start": [],
        "hostname": "",
        "pid": 0,
        "io_type": "",
        "req_size": [],
        "total_bytes": 0,
        "total_iops": 0,
        "t_flush": 0.0,
    }

    # 1) overlap for rank level metrics
    for file_or_msg in files_or_msgs:
        # print(files_or_msgs.index(file_or_msg))
        data_rank, ext = parse(
            file_or_msg, data_rank, io_type=args.mode[0], debug_level=0
        )
        # print(data_rank)

    # 2) exit if no new data
    if not data_rank["avg_throughput"]:
        data_rank, ext = parse(file_or_msg, data_rank, io_type="read")
        # print(data_rank)
        if not data_rank["avg_throughput"]:
            CONSOLE.print("[red]Terminating prediction (no data passed) [/]")
        else:
            CONSOLE.print("[red]Read data passed -- ignoring [/]")
        exit(0)

    # 3) Scale if JSON or MsgPack
    b_rank = np.array(data_rank["avg_throughput"])
    t_rank_s = np.array(data_rank["t_start"])
    t_rank_e = np.array(data_rank["t_end"])

    # 4) app level bandwidth
    b, t = overlap(b_rank, t_rank_s, t_rank_e)

    # Debug
    dt = np.diff(t)  # time intervals
    bytes_total = np.sum(b[:-1] * dt)  # total bytes
    print(
        f"Total transferred in this burst: {bytes_total:.0f} bytes ({bytes_total/1e9:.3f} GB)"
    )

    # # 5) Extend for ZMQ
    if "ZMQ" in ext.upper():
        # extend data
        b_app.extend(b)
        t_app.extend(t)
        b = np.array(b_app[:])
        t = np.array(t_app[:])
        # print(f"App Bandwidth: {b_app}")
        # print(f"App Time: {t_app}")
        # 5) overlap with app bandwdith so far
        # b, t = overlap_two_series(b_app[:], t_app[:], b, t)
        # t_app = t.tolist()
        # b_app = b.tolist()
        # print(f"App Bandwidth: {b_app}")
        # print(f"App Time: {t_app}")

    else:
        b = np.array(list(b))
        t = np.array(list(t))

    # save the bandwidth
    process = handle_in_process(
        dump_json,
        args=(b, t),
    )

    # 6) plot to check:
    if any(x in args.engine for x in ["mat", "plot"]):
        fig = go.Figure()
        unit, order = set_unit(b)
        # fig.add_trace(go.Scatter(x=t, y=b * order, name="App Bandwidth",mode='lines+markers'))
        fig.add_trace(
            go.Scatter(x=t, y=b * order, name="App Bandwidth", line={"shape": "hv"})
        )
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
    prediction, analysis_figures = core(data, args)

    # 9) plot and print info
    # if args.verbose:
    display_prediction(args, prediction)

    analysis_figures.show()
    process.join()

    return prediction, args, data_rank["t_flush"]


if __name__ == "__main__":
    # absolute path to search all text files_or_msgs inside a specific folder
    # path=r'/d/github/FTIO/examples/API/gekkoFs/JSON/*.json'
    # path = r"/d/github/FTIO/examples/API/gekkoFs/MSGPACK/write*.msgpack"
    path = r"/d/Downloads/metrics/metrics/write_*.msgpack"
    matched_files_or_msgs = glob.glob(path)
    run(matched_files_or_msgs)
