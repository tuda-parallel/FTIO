import numpy as np

from ftio.freq._stft_workflow import ftio_stft
from ftio.parse.args import parse_args


def test_ftio_stft_sequence():
    """Test that STFT returns a sequence of dominant frequencies when the signal is non-stationary."""
    fs = 100
    t = np.arange(0, 5, 1 / fs)
    # 5Hz for first half, 10Hz for second half
    bandwidth = np.zeros_like(t)
    bandwidth[: len(t) // 2] = np.sin(2 * np.pi * 5 * t[: len(t) // 2])
    bandwidth[len(t) // 2 :] = np.sin(2 * np.pi * 10 * t[len(t) // 2 :])

    args = parse_args(["-tr", "stft", "-e", "no"], "ftio")
    args.freq = fs

    prediction, _ = ftio_stft(args, bandwidth, t)

    # Should have multiple segments
    assert len(prediction.dominant_freq) > 1
    # Should find 5Hz and 10Hz
    assert any(np.isclose(prediction.dominant_freq, 5, atol=1))
    assert any(np.isclose(prediction.dominant_freq, 10, atol=1))


def test_ftio_stft_frequency_jump():
    """Test STFT tracking with a 50Hz to 120Hz jump, as per user example."""
    fs = 1000
    t = np.arange(0, 1.0, 1 / fs)
    # 50Hz for first half, 120Hz for second half
    bandwidth = np.sin(2 * np.pi * 50 * t) * (t < 0.5) + np.sin(2 * np.pi * 120 * t) * (
        t >= 0.5
    )

    args = parse_args(["-tr", "stft", "-e", "no"], "ftio")
    args.freq = fs

    prediction, _ = ftio_stft(args, bandwidth, t)

    # Check first half (around index 2-3 of STFT windows)
    # With fs=1000 and default nperseg=256, windows are ~0.25s wide
    assert any(
        np.isclose(
            prediction.dominant_freq[: len(prediction.dominant_freq) // 2], 50, atol=5
        )
    )
    # Check second half
    assert any(
        np.isclose(
            prediction.dominant_freq[len(prediction.dominant_freq) // 2 :], 120, atol=10
        )
    )


def test_ftio_stft_top_freqs():
    """Test that top_freqs is populated for STFT if n_freq is set."""
    fs = 100
    t = np.arange(0, 5, 1 / fs)
    bandwidth = np.sin(2 * np.pi * 5 * t)

    args = parse_args(["-tr", "stft", "-e", "no", "-n", "3"], "ftio")
    args.freq = fs

    prediction, _ = ftio_stft(args, bandwidth, t)

    assert "freq" in prediction.top_freqs
    assert len(prediction.top_freqs["freq"]) == 3
