import numpy as np
import time
from argparse import Namespace
from ftio.freq._astft import astft
from ftio.freq.discretize import sample_data
from ftio.freq.helper import MyConsole

def ftio_astft(
    args: Namespace,
    bandwidth: np.ndarray,
    time_b: np.ndarray,
    total_bytes: int,
    ranks: int,
    text: str = "",
):

    # Default values for variables
    share = {}
    df_out = [[], [], [], []]
    prediction = {
        "source": {args.transformation},
        "dominant_freq": [],
        "conf": [],
        "t_start": 0,
        "t_end": 0,
        "total_bytes": 0,
        "freq": 0,
        "ranks": 0,
    }
    console = MyConsole(verbose=args.verbose)

    #  Extract time series: Sample the bandwidth evenly spaced in time
    tik = time.time()
    console.print("[cyan]Executing:[/] Discretization\n")
    b_sampled, freq = sample_data(
        bandwidth, time_b, args.freq, args.verbose
    )
    console.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")

    astft(b_sampled, freq, bandwidth, time_b)

    return prediction, df_out, share