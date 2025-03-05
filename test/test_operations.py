"""
Functions for testing the API functionalities of the ftio package.
"""

import os
from ftio.parse.bandwidth import overlap
from ftio.plot.freq_plot import convert_and_plot
from ftio.processing.operations import quick_ftio
from ftio.processing.post_processing import label_phases
from ftio.cli.ftio_core import main

def test_quick_ftio():
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
    argv =["-e", "no"]
    _ = quick_ftio(argv, b, t, total_bytes, ranks)
    assert True



def test_post_processing():
    """Test the plotting functionality of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no"]
    prediction, args = main(args)
    _ = label_phases(prediction[-1], args)
    assert True 


def test_ftio_multiple_files():
    """Test the plotting functionality of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, file, "-e", "no"]
    _, args = main(args)
    assert True 