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
    args = parse_args(["-e", "no", "-c", "-tr", "wave_cont"], "ftio")
    _ = core([], args)
    assert True


def test_wavelet_disc_args():
    """Test discrete wavelet transformation with default decomposition level."""
    args = parse_args(["-e", "no", "-c", "-tr", "wave_disc"], "ftio")
    _ = core([], args)
    assert True


def test_wavelet_cont_lvl_args():
    """Test continuous wavelet transformation with a specified decomposition level."""
    args = parse_args(["-e", "no", "-c", "-tr", "wave_cont", "-le", "5"], "ftio")
    _ = core([], args)
    assert True


def test_wavelet_disc_lvl_args():
    """Test discrete wavelet transformation with a specified decomposition level."""
    args = parse_args(["-e", "no", "-c", "-tr", "wave_disc", "-le", "5"], "ftio")
    _ = core([], args)
    assert True


####################################################################################################
# Test wavelet functionality
####################################################################################################


def test_wavelet_cont():
    """Test the core functionality of ftio with frequency option."""
    file = os.path.join(
        os.path.dirname(__file__),
        "../examples/tmio/ior/collective/1536_new.json",
    )
    args = ["ftio", file, "-e", "no", "-c", "-tr", "wave_cont"]
    _, args = main(args)
    assert True
