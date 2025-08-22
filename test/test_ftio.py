"""
Functions for testing the core functionalities of the ftio package.
"""

import os

from ftio.cli.ftio_core import core, main
from ftio.parse.args import parse_args
from ftio.processing.print_output import display_prediction


def test_ftio_core_no_input():
    """Test the core functionality of ftio with no input and no extra options."""
    args = parse_args(["-e", "no"], "ftio")
    _ = core({}, args)
    assert True


def test_ftio_core_no_input_autocorrelation():
    """Test the core functionality of ftio with no input and autocorrelation."""
    args = parse_args(["-e", "no", "-au"], "ftio")
    _ = core({}, args)
    assert True


def test_ftio_core():
    """Test the core functionality of ftio with no extra options."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = [
        "ftio",
        file,
        "-e",
        "no",
    ]
    _ = core({}, args)
    assert True


def test_ftio_core_autocorrelation():
    """Test the core functionality of ftio with autocorrelation."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "-au"]
    _ = core({}, args)
    assert True


def test_ftio_n_freq():
    """Test the core functionality of ftio with obtaining n frequencies."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "-n", "5"]
    _, args = main(args)
    assert True


def test_ftio_zscore():
    """Test the z-score prediction of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no"]
    prediction, args = main(args)
    assert prediction[-1].t_start == 0.05309


def test_ftio_dbscan():
    """Test the DBSCAN clustering option of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "-o", "dbscan"]
    prediction, args = main(args)
    assert prediction[-1].t_start == 0.05309


def test_ftio_lof():
    """Test the LOF clustering option of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "-o", "lof"]
    prediction, args = main(args)
    assert prediction[-1].t_start == 0.05309


def test_ftio_dtw():
    """Test DTW option of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "-d"]
    prediction, args = main(args)
    assert prediction[-1].t_start == 0.05309


def test_ftio_display_prediction():
    """Test the display prediction functionality of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no"]
    prediction, args = main(args)
    display_prediction(args, prediction)
    assert True
