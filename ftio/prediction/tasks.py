
import numpy as np
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.plot.freq_plot import convert_and_plot
from ftio.processing.print_output import display_prediction
# from ftio.prediction.helper import get_dominant
# from ftio.plot.freq_plot import convert_and_plot
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()
CONSOLE.set(True)

#TODO: extend this similar to ftio/prediction/analysis.py

def ftio_metric_task(metric:str, arrays:np.ndarray, argv:list, ranks:int = 0, show:bool=True) -> dict:
    """generate FTIO prediction from 2d np array

    Args:
        metric (str): Name of metric
        arrays (np.ndarray): 2D np array containing the bandwidth and time
        argv (list): List of args for ftio
        ranks (int): Number of ranks
        show (bool): show the prediction result

    Returns:
        dict: prediction from FTIO (see core from ftio.cli.ftio_core)
    """
    if len(arrays[0]) > 1:
        # set up data
        data = {"bandwidth": arrays[0], "time": arrays[1], "total_bytes": 0, "ranks": ranks}

        # parse args
        args = parse_args(argv, "ftio")

        # perform prediction
        prediction, dfs = core(data, args)

        # # plot and print info
        # convert_and_plot(args, dfs, len(data))
        if show:
            CONSOLE.info(f"\n[green underline]Metric: {metric}[/]")
            display_prediction(args, prediction)

        if any(x in args.engine for x in ["mat", "plot"]):
            convert_and_plot(args, dfs)
        
        return prediction


def ftio_metric_task_save(data, metric:str, arrays:np.ndarray, argv:list, ranks:int, show:bool=False) -> None:
    prediction = ftio_metric_task(metric, arrays ,argv ,ranks, show)
    # freq = get_dominant(prediction) #just get a single dominant value
    if prediction:
        data.append({
            "metric": f"{metric}",
            "dominant_freq": prediction["dominant_freq"],
            "conf": prediction["conf"],
            "amp": prediction["amp"],
            "phi": prediction["phi"],
            "t_start": prediction["t_start"],
            "t_end": prediction["t_end"],
            "total_bytes": prediction["total_bytes"],
            "ranks": prediction["ranks"],
            "freq": prediction["freq"],
            **({"top_freq": prediction["top_freq"]} if "top_freq" in prediction else {})
            }
        )
    else:
        CONSOLE.info(f"\n[yellow underline]Warning: {metric} returned {prediction}[/]")
