"""
Functions for filters.
"""

import os

from ftio.cli.ftio_core import main


def test_lowpass():
    """Test the lowpass filter functionality of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = [
        "ftio",
        file,
        "-e",
        "no",
        "--filter_type",
        "lowpass",
        "--filter_cutoff",
        "1",
    ]
    prediction, parsed_args = main(args)
    assert len(prediction) > 0
    assert not prediction[-1].is_empty()
    assert prediction[-1].t_start == 0.05309


def test_highpass():
    """Test the highpass filter functionality of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = [
        "ftio",
        file,
        "-e",
        "no",
        "--filter_type",
        "highpass",
        "--filter_cutoff",
        "0.2",
    ]
    prediction, parsed_args = main(args)
    assert len(prediction) > 0
    assert not prediction[-1].is_empty()
    assert prediction[-1].t_start == 0.05309


def test_bandpass():
    """Test the bandpass filter functionality of ftio."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = [
        "ftio",
        file,
        "-e",
        "no",
        "--filter_type",
        "bandpass",
        "--filter_cutoff",
        "0.1",
        "0.9",
    ]
    prediction, parsed_args = main(args)
    assert len(prediction) > 0
    assert not prediction[-1].is_empty()
    assert prediction[-1].t_start == 0.05309
