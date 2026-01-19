"""
Functions for testing the wavelet functionality of the ftio package.
"""

import os

from ftio.cli.ftio_core import core, main
from ftio.parse.args import parse_args

####################################################################################################
# Test wavelet Args
####################################################################################################


def test_wavelet_cont_args():
    """Test continuous wavelet transformation with default decomposition level."""
    args = parse_args(["-e", "no", "-tr", "wave_cont"], "ftio")
    pred, analysis_figs = core([], args)

    assert pred.is_empty()
    assert analysis_figs is not None


def test_wavelet_disc_args():
    """Test discrete wavelet transformation with default decomposition level."""
    args = parse_args(["-e", "no", "-tr", "wave_disc"], "ftio")
    pred, analysis_figs = core([], args)

    assert pred.is_empty()
    assert analysis_figs is not None


def test_wavelet_cont_lvl_args():
    """Test continuous wavelet transformation with a specified decomposition level."""
    args = parse_args(["-e", "no", "-tr", "wave_cont", "-le", "5"], "ftio")
    pred, analysis_figs= core([], args)

    assert args.level == 5
    assert pred.is_empty()


def test_wavelet_disc_lvl_args():
    """Test discrete wavelet transformation with a specified decomposition level."""
    args = parse_args(["-e", "no", "-tr", "wave_disc", "-le", "5"], "ftio")
    pred, analysis_figs = core([], args)

    assert args.level == 5
    assert pred.is_empty()


####################################################################################################
# Test wavelet functionality
####################################################################################################


def test_wavelet_cont():
    """Test the core functionality of ftio with frequency option."""
    file = os.path.join(
        os.path.dirname(__file__),
        "../examples/tmio/ior/collective/1536_new.json",
    )
    args = ["ftio", file, "-e", "no", "-tr", "wave_cont"]
    pred, args = main(args)

    assert len(pred) > 0
    assert not pred[-1].is_empty()
    assert pred[-1].source == "wave_cont"

