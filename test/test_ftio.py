"""
Functions for testing the core functionalities of the ftio package.
"""

import os
from ftio.cli.ftio_core import main, core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.post.processing import label_phases

def test_ftio():
    """Test the core functionality of ftio with no extra options."""
    args = parse_args(["-e", "no"], "ftio")
    _ = core([], args)
    assert True

def test_ftio_autocorrelation():
    """Test the core functionality of ftio with autocorrelation option."""
    args = parse_args(["-e", "no", "-c"], "ftio")
    _ = core([], args)
    assert True

def test_ftio_n_freq():
    """Test the core functionality of ftio with frequency option."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "-n", "5"]
    _, args = main(args)
    assert True

def test_ftio_zscore():
    """Test the z-score prediction of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no"]
    prediction, args = main(args)
    assert prediction["t_start"] == 0.05309

def test_ftio_dbscan():
    """Test the DBSCAN clustering option of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "-o", "dbscan"]
    prediction, args = main(args)
    assert prediction["t_start"] == 0.05309

def test_ftio_lof():
    """Test the LOF clustering option of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "-o", "lof"]
    prediction, args = main(args)
    assert prediction["t_start"] == 0.05309

def test_ftio_plot():
    """Test the plotting functionality of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no"]
    prediction, args = main(args)
    _ = label_phases(prediction, args)
    assert True 

def test_ftio_display_prediction():
    """Test the display prediction functionality of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no"]
    prediction, args = main(args)
    display_prediction("ftio", prediction)
    assert True