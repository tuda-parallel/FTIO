"""
Functions for testing the API functionalities of the ftio package.
"""

import os

import numpy as np

from ftio.cli.ftio_core import main
from ftio.freq.prediction import Prediction
from ftio.parse.bandwidth import overlap
from ftio.processing.compact_operations import quick_ftio
from ftio.processing.post_processing import label_phases


def test_quick_ftio():
    """Test quick_ftio function returns valid object"""
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
    argv = ["-e", "no"]
    prediction = quick_ftio(argv, b, t, total_bytes, ranks)

    assert isinstance(prediction, Prediction)
    assert not prediction.is_empty()
    assert prediction.t_start == 0.0
    assert prediction.t_end == 65.0
    assert prediction.source == "dft"
    assert len(prediction.dominant_freq) > 0
    assert np.isclose(
        prediction.dominant_freq[0], 0.04615385, rtol=1e-5
    )  # Is found frequency correct?


def test_post_processing():
    """Test the plotting functionality of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no"]
    prediction, args = main(args)
    phases, time = label_phases(prediction[-1], args)

    assert isinstance(phases, list)
    assert len(phases) > 0
    assert isinstance(time, dict)
    assert "t_s" in time
    assert "t_e" in time
    assert len(time["t_s"]) == len(time["t_e"])
    assert all(isinstance(phase, int) for phase in phases)


def test_ftio_multiple_files():
    """Test multiple files at once"""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, file, "-e", "no"]

    preds, parsed_args = main(args)

    # It seems that same files conclude to one file
    assert isinstance(preds, list)
    assert len(preds) == 1  # Identical export file.
    for pred in preds:
        assert isinstance(pred, Prediction)
        assert not pred.is_empty()
        assert pred.t_start == 0.05309
