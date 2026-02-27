"""
Author: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Version: 0.0.8
Date: Feb 2026

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import importlib.util

import numpy as np
import pytest

from ftio.parse.args import parse_args

# Check if required libraries are available
vmdpy_available = importlib.util.find_spec("vmdpy") is not None
pysdkit_available = importlib.util.find_spec("pysdkit") is not None
tftb_available = importlib.util.find_spec("tftb") is not None
package_available = vmdpy_available and pysdkit_available and tftb_available

if package_available:
    from ftio.freq._astft_workflow import ftio_astft


@pytest.mark.skipif(not package_available, reason="vmdpy, pysdkit or tftb not installed")
def test_ftio_astft_sequence():
    """Test that ASTFT returns a sequence of dominant frequencies when the
    signal is non-stationary."""
    fs = 100
    t = np.arange(0, 10, 1 / fs)
    # 5Hz for first half, 10Hz for second half
    bandwidth = np.zeros_like(t)
    bandwidth[: len(t) // 2] = np.sin(2 * np.pi * 5 * t[: len(t) // 2])
    bandwidth[len(t) // 2 :] = np.sin(2 * np.pi * 10 * t[len(t) // 2 :])

    args = parse_args(["-tr", "astft", "-e", "no"], "ftio")
    args.freq = fs

    prediction, _ = ftio_astft(args, bandwidth, t, total_bytes=0, ranks=1)

    # Check if we have at least two components
    assert len(prediction.dominant_freq) >= 2

    # Check if frequencies are close to 5 and 10 Hz
    assert any(np.isclose(prediction.dominant_freq, 5, atol=1))
    assert any(np.isclose(prediction.dominant_freq, 10, atol=1))


@pytest.mark.skipif(not package_available, reason="vmdpy, pysdkit or tftb not installed")
def test_ftio_astft_ranges():
    """Test that ASTFT correctly identifies time ranges for components."""
    fs = 100
    t = np.arange(0, 10, 1 / fs)
    bandwidth = np.sin(2 * np.pi * 5 * t)

    args = parse_args(["-tr", "astft", "-e", "no"], "ftio")
    args.freq = fs

    prediction, _ = ftio_astft(args, bandwidth, t, total_bytes=0, ranks=1)

    assert len(prediction.ranges) > 0
    # Check that ranges are within trace bounds
    for start, end in prediction.ranges:
        assert start >= t[0] - 0.1
        assert end <= t[-1] + 0.1
