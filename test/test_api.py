"""
Functions for testing the API functionalities of the ftio package.
"""

import numpy as np
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.plot.freq_plot import convert_and_plot
from ftio.parse.bandwidth import overlap


def test_api():
    """Test the API functionality of ftio."""
    ranks = 10
    total_bytes = 100
    b_rank = [
        0.0,
        0.0,
        1000.0,
        1000.0,
        0.0,
        0.0,
        1000.0,
        1000.0,
        0.0,
        0.0,
        1000.0,
        1000.0,
        0.0,
        0.0,
    ]
    t_rank_s = [
        0.5,
        0.0,
        10.5,
        10.0,
        20.5,
        20.0,
        30.5,
        30.0,
        40.5,
        40.0,
        50.5,
        50.0,
        60.5,
        60,
    ]
    t_rank_e = [
        5.0,
        4.5,
        15.0,
        14.5,
        25.0,
        24.5,
        35.0,
        34.5,
        45.0,
        44.5,
        55.0,
        54.5,
        65.0,
        64.5,
    ]
    b, t = overlap(b_rank, t_rank_s, t_rank_e)
    # command line arguments
    argv = ["-e", "no"]  # ["-e", "mat"]
    # set up data
    data = {
        "time": np.array(t),
        "bandwidth": np.array(b),
        "total_bytes": total_bytes,
        "ranks": ranks,
    }
    # parse args
    args = parse_args(argv, "ftio")
    # perform prediction
    prediction, dfs = core([data], args)
    # plot and print info
    convert_and_plot(args, dfs, len(data))
    display_prediction("ftio", prediction)
    assert True
