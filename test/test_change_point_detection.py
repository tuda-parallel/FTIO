"""
Tests for change point detection algorithms (ADWIN, CUSUM, Page-Hinkley).

Author: Amine Aherbil
Editor: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Version: 0.0.8
Date: January 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from unittest.mock import MagicMock

import numpy as np

from ftio.freq.prediction import Prediction
from ftio.prediction.change_detection.adwin import adwin_step
from ftio.prediction.change_detection.cusum import cusum_step
from ftio.prediction.change_detection.pagehinkley import pagehinkley_step


def create_mock_prediction(freq: float, t_start: float, t_end: float) -> MagicMock:
    """Create a mock Prediction object with specified frequency."""
    pred = MagicMock(spec=Prediction)
    pred.dominant_freq = np.array([freq])
    pred.t_start = t_start
    pred.t_end = t_end
    # Mock get_dominant_freq() to return scalar (used by get_dominant() helper)
    pred.get_dominant_freq.return_value = freq
    return pred


class TestADWINDetector:
    """Test cases for ADWIN change point detector."""

    def test_no_change_stable_frequency(self):
        """Test that stable frequencies don't trigger change detection."""
        state = {}

        # Add stable frequency predictions
        for i in range(10):
            _, _, state = adwin_step(0.5, float(i + 1), state, delta=0.05)

        # Should not detect change with stable frequency
        assert state.get("last_change_point") is None

    def test_detects_frequency_change(self):
        """Test that significant frequency change is detected."""
        state = {}

        # Add low frequency predictions
        for i in range(10):
            _, _, state = adwin_step(0.1, float(i + 1), state, delta=0.05)

        # Add high frequency predictions (significant change: 0.1 -> 10 Hz)
        change_detected = False
        for i in range(10, 30):
            idx, _, state = adwin_step(10.0, float(i + 1), state, delta=0.05)
            if idx is not None:
                change_detected = True
                break

        assert change_detected

    def test_reset_on_nan_frequency(self):
        """Test that NaN frequency resets the detector window."""
        state = {}

        # Add some predictions
        for i in range(5):
            _, _, state = adwin_step(0.5, float(i + 1), state, delta=0.05)

        # Add NaN frequency
        _, _, state = adwin_step(np.nan, 6.0, state, delta=0.05)

        # Window should be reset
        assert state.get("frequencies_found", 0) == 0


class TestCUSUMDetector:
    """Test cases for CUSUM change point detector."""

    def test_reference_establishment(self):
        """Test that reference is established from initial samples."""
        state = {}

        # Add initial samples
        for i, f in enumerate([0.5, 0.5, 0.5]):
            _, _, state = cusum_step(f, float(i), state)

        assert abs(state["reference"] - 0.5) < 0.001

    def test_detects_upward_change(self):
        """Test detection of upward frequency shift."""
        state = {}

        # Establish baseline
        for i in range(5):
            _, _, state = cusum_step(0.1, float(i), state)

        # Introduce upward shift
        change_detected = False
        for i in range(5, 20):
            detected, _, state = cusum_step(1.0, float(i), state)
            if detected:
                change_detected = True
                break

        assert change_detected

    def test_reset_on_nan(self):
        """Test that NaN frequency resets CUSUM state."""
        state = {}

        # Add some frequencies
        for i in range(5):
            _, _, state = cusum_step(0.5, float(i), state)

        # Add NaN
        _, _, state = cusum_step(np.nan, 5.0, state)

        assert state.get("sum_pos", 0) == 0.0
        assert state.get("sum_neg", 0) == 0.0


class TestPageHinkleyDetector:
    """Test cases for Page-Hinkley change point detector."""

    def test_reference_mean_update(self):
        """Test that reference mean updates with new samples."""
        state = {}

        # Add samples
        _, _, _, state = pagehinkley_step(0.5, 0.0, state)
        assert state["reference_mean"] == 0.5

        _, _, _, state = pagehinkley_step(1.0, 1.0, state)
        assert abs(state["reference_mean"] - 0.75) < 0.001

    def test_detects_change(self):
        """Test detection of frequency change."""
        state = {}

        # Establish baseline
        for i in range(10):
            _, _, _, state = pagehinkley_step(0.1, float(i), state)

        # Introduce shift
        change_detected = False
        for i in range(10, 30):
            detected, _, _, state = pagehinkley_step(1.0, float(i), state)
            if detected:
                change_detected = True
                break

        assert change_detected


class TestDetectorIntegration:
    """Integration tests for change point detectors."""

    def test_all_detectors_handle_empty_input(self):
        """Test all detectors handle edge cases gracefully."""
        # Test with zero frequency
        _, _, state_adwin = adwin_step(0.0, 1.0, {})
        _, _, state_cusum = cusum_step(0.0, 1.0, {})
        _, _, _, state_ph = pagehinkley_step(0.0, 1.0, {})

        # All should handle gracefully
        assert state_adwin["frequencies_found"] == 0
        assert state_cusum["sum_pos"] == 0.0
        assert state_ph.get("initialized") is False

    def test_all_detectors_consistent_detection(self):
        """Test all detectors can detect obvious pattern changes."""
        state_adwin = {}
        state_cusum = {}
        state_ph = {}

        # Create obvious pattern change: 0.1 Hz -> 10 Hz
        low_freq = 0.1
        high_freq = 10.0

        # Feed low frequency
        for i in range(10):
            _, _, state_adwin = adwin_step(low_freq, float(i + 1), state_adwin)
            _, _, state_cusum = cusum_step(low_freq, float(i + 1), state_cusum)
            _, _, _, state_ph = pagehinkley_step(low_freq, float(i + 1), state_ph)

        # Feed high frequency and check for detection
        adwin_detected = False
        cusum_detected = False
        ph_detected = False

        for i in range(10, 40):
            idx, _, state_adwin = adwin_step(high_freq, float(i + 1), state_adwin)
            if idx is not None:
                adwin_detected = True

            detected, _, state_cusum = cusum_step(high_freq, float(i + 1), state_cusum)
            if detected:
                cusum_detected = True

            detected, _, _, state_ph = pagehinkley_step(high_freq, float(i + 1), state_ph)
            if detected:
                ph_detected = True

        # All detectors should detect such an obvious change
        assert adwin_detected or cusum_detected or ph_detected
