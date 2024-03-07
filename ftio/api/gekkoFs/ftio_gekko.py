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

def run(files:list,argv = ["-e", "plotly", "-f", "100"] ): #"0.01"] ):
    """Executes ftio on list of files.

    Args:
        files (list): _description_
        argv: command line arguments from ftio
    """
    
    #parse args
    args = parse_args(argv,"ftio")
    ranks = len(files)

    # Set up data
    data = {
                'avg_thruput_mib': [],
                'end_t_micro': [],
                'start_t_micro': [],
                'hostname': '',
                'pid': 0,
                'req_size': [],
                'total_bytes': 0,
                'total_iops': 0
            }

    ## 1) overlap for rank level metrics
    for file in files:
        data, ext = parse(file,data)

    ## 2) Scale if JSON
    scale = [1, 1e-6, 1e-6]
    if "JSON" in ext.upper(): 
        scale = [1.07*1e+6, 1e-3, 1e-3]
    
    b_rank = np.array(data['avg_thruput_mib'])*scale[0]
    t_rank_s = np.array(data['start_t_micro'])*scale[1]
    t_rank_e = np.array(data['end_t_micro'])*scale[2]

    ## 3) app level bandwidth
    b,t = overlap(b_rank,t_rank_s, t_rank_e)
    t = np.array(t)
    b = np.array(b)

    ## 4) plot to check:
    if any(x in args.engine for x in ["mat","plot"]):
        fig = go.Figure()
        unit, order = set_unit(b)
        fig.add_trace(go.Scatter(x=t, y=b*order,name="App Bandwidth"))
        fig.update_layout(xaxis_title="Time (s)",yaxis_title=f"Bandwidth ({unit})")
        fig = format_plot(fig)
        fig.show()

    # set up data
    data= {
            "time": t,
            "bandwidth": b,
            "total_bytes": data['total_bytes'],
            "ranks": ranks 
            }



    # perform prediction
    prediction, dfs = core([data], args)

    # plot and print info
    display_prediction(["./ftio"], prediction)
    convert_and_plot(data, dfs, args)

    return prediction, args


if __name__ == "__main__":
    # absolute path to search all text files inside a specific folder
    # path=r'/d/github/FTIO/examples/gekkoFs/JSON/*.json'
    path=r'/d/github/FTIO/examples/gekkoFs/MSGPACK/write*.msgpack'
    matched_files = glob.glob(path)
    run(matched_files)
