"""Tests wavelet functionality
"""

from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args


def test_wavelet_cont():
    """
    Test continuous wavelet transformation with default decomposition level.
    """
    args = parse_args(["-e", "no", "-c", "-tr", "wave_cont"], "ftio")
    _ = core([], args)
    assert True


def test_wavelet_disc():
    """
    Test discrete wavelet transformation with default decomposition level.
    """
    args = parse_args(["-e", "no", "-c", "-tr", "wave_disc"], "ftio")
    _ = core([], args)
    assert True


def test_wavelet_cont_lvl():
    """
    Test continuous wavelet transformation with a specified decomposition level.
    """
    args = parse_args(["-e", "no", "-c", "-tr", "wave_cont", "-le", "5"], "ftio")
    _ = core([], args)
    assert True


def test_wavelet_disc_lvl():
    """
    Test discrete wavelet transformation with a specified decomposition level.
    """
    args = parse_args(["-e", "no", "-c", "-tr", "wave_disc", "-le", "5"], "ftio")
    _ = core([], args)
    assert True
