import importlib.util

import numpy as np
import pytest

from ftio.parse.args import parse_args

# Check if required libraries are available
vmdpy_available = importlib.util.find_spec("vmdpy") is not None
pysdkit_available = importlib.util.find_spec("pysdkit") is not None

if vmdpy_available or pysdkit_available:
    from ftio.freq._amd_workflow import ftio_amd


@pytest.mark.skipif(not vmdpy_available, reason="vmdpy not installed")
def test_ftio_vmd():
    """Test that VMD returns components when the signal is non-stationary."""
    fs = 100
    t = np.arange(0, 10, 1 / fs)
    # 5Hz for first half, 10Hz for second half
    bandwidth = np.zeros_like(t)
    bandwidth[: len(t) // 2] = np.sin(2 * np.pi * 5 * t[: len(t) // 2])
    bandwidth[len(t) // 2 :] = np.sin(2 * np.pi * 10 * t[len(t) // 2 :])

    args = parse_args(["-tr", "vmd", "-e", "no"], "ftio")
    args.freq = fs

    prediction, _ = ftio_amd(args, bandwidth, t, total_bytes=0, ranks=1)

    # Check if we have components
    assert len(prediction.dominant_freq) >= 1
    # Check for target frequencies
    assert any(np.isclose(prediction.dominant_freq, 5, atol=1)) or any(
        np.isclose(prediction.dominant_freq, 10, atol=1)
    )


@pytest.mark.skipif(not pysdkit_available, reason="pysdkit not installed")
def test_ftio_efd():
    """Test that EFD returns components."""
    fs = 100
    t = np.arange(0, 10, 1 / fs)
    bandwidth = np.sin(2 * np.pi * 5 * t)

    args = parse_args(["-tr", "efd", "-e", "no"], "ftio")
    args.freq = fs

    prediction, _ = ftio_amd(args, bandwidth, t, total_bytes=0, ranks=1)

    assert len(prediction.dominant_freq) >= 1
    assert any(np.isclose(prediction.dominant_freq, 5, atol=1))
