"""
Functions for filters.
"""

import os
from ftio.cli.ftio_core import core

def test_lowpass():
    """Test the core functionality of ftio with no extra options."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "--filter_type " , "lowpass", "--filter_cutoff", "1"]
    _ = core({}, args)
    assert True

def test_highpass():
    """Test the core functionality of ftio with no extra options."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "--filter_type " , "highpass", "--filter_cutoff", "0.2"]
    _ = core({}, args)
    assert True

def test_bandpass():
    """Test the core functionality of ftio with no extra options."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no", "--filter_type " , "bandpass", "--filter_cutoff", "0.01", "5"]
    _ = core({}, args)
    assert True

    