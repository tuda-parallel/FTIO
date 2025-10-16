import numpy as np
import time
from argparse import Namespace
from ftio.freq._amd import amd
from ftio.freq.discretize import sample_data
from ftio.freq.helper import MyConsole
from ftio.freq.prediction import Prediction

def ftio_amd(
    args: Namespace,
    bandwidth: np.ndarray,
    time_samples: np.ndarray,
    total_bytes: int,
    ranks: int,
    text: str = "",
):
    # Default values for variables
    share = {}
    df_out = [[], [], [], []]
    prediction = Prediction(args.transformation)
    console = MyConsole(verbose=args.verbose)

    #  Extract time series: Sample the bandwidth evenly spaced in time
    tik = time.time()
    console.print("[cyan]Executing:[/] Discretization\n")
    b_sampled, freq = sample_data(bandwidth, time_samples, args)
    console.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")

    amd(b_sampled, freq, bandwidth, time_samples, args)

    return prediction, df_out, share
