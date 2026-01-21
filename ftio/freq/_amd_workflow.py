"""
AMD workflow for FTIO. This module implements Adaptive Mode Decomposition (AMD)
based frequency analysis for FTIO. It provides functionality to identify periodic
time windows in bandwidth time-series using Variational Mode Decomposition
(VMD) and Empirical Fourier Decomposition (EFD). The results are integrated
with FTIO’s prediction and reporting framework.

Author: josefinez
Editor: Ahmad Tarraf
Copyright (c) 2026 TU Darmstadt, Germany
Date: Oct 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

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

    # TODO: actually fill the prediction of FTIO
    amd(b_sampled, freq, time_samples, args)

    return prediction, df_out, share
