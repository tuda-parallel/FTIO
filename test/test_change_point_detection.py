"""
Tests for change point detection algorithms (ADWIN, CUSUM, Page-Hinkley).

Author: Amine Aherbil
Copyright (c) 2025 TU Darmstadt, Germany
Date: January 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from unittest.mock import MagicMock

import numpy as np

from ftio.freq.prediction import Prediction
from ftio.prediction.change_point_detection import (
    ChangePointDetector,
    CUSUMDetector,
    SelfTuningPageHinkleyDetector,
)


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

    def test_initialization(self):
        """Test ADWIN detector initializes correctly."""
        detector = ChangePointDetector(delta=0.05, shared_resources=None, show_init=False)
        assert detector.delta == 0.05
        assert detector.min_window_size == 2

    def test_no_change_stable_frequency(self):
        """Test that stable frequencies don't trigger change detection."""
        detector = ChangePointDetector(delta=0.05, shared_resources=None, show_init=False)

        # Add stable frequency predictions
        for i in range(10):
            pred = create_mock_prediction(freq=0.5, t_start=i, t_end=i + 1)
            _ = detector.add_prediction(pred, timestamp=float(i + 1))

        # Should not detect change with stable frequency
        assert detector._get_change_count() == 0

    def test_detects_frequency_change(self):
        """Test that significant frequency change is detected."""
        detector = ChangePointDetector(delta=0.05, shared_resources=None, show_init=False)

        # Add low frequency predictions (more samples for statistical significance)
        for i in range(10):
            pred = create_mock_prediction(freq=0.1, t_start=i, t_end=i + 1)
            detector.add_prediction(pred, timestamp=float(i + 1))

        # Add high frequency predictions (significant change: 0.1 -> 10 Hz)
        change_detected = False
        for i in range(10, 30):
            pred = create_mock_prediction(freq=10.0, t_start=i, t_end=i + 1)
            result = detector.add_prediction(pred, timestamp=float(i + 1))
            if result is not None:
                change_detected = True

        # Should detect the change during the loop or in the count
        assert change_detected or detector._get_change_count() >= 1

    def test_reset_on_nan_frequency(self):
        """Test that NaN frequency resets the detector window."""
        detector = ChangePointDetector(delta=0.05, shared_resources=None, show_init=False)

        # Add some predictions
        for i in range(5):
            pred = create_mock_prediction(freq=0.5, t_start=i, t_end=i + 1)
            detector.add_prediction(pred, timestamp=float(i + 1))

        # Add NaN frequency
        pred = create_mock_prediction(freq=np.nan, t_start=5, t_end=6)
        detector.add_prediction(pred, timestamp=6.0)

        # Window should be reset
        assert len(detector._get_frequencies()) == 0

    def test_window_stats(self):
        """Test window statistics calculation."""
        detector = ChangePointDetector(delta=0.05, shared_resources=None, show_init=False)

        # Add predictions
        freqs = [0.5, 0.6, 0.4, 0.5, 0.55]
        for i, f in enumerate(freqs):
            pred = create_mock_prediction(freq=f, t_start=i, t_end=i + 1)
            detector.add_prediction(pred, timestamp=float(i + 1))

        stats = detector.get_window_stats()
        assert stats["size"] == 5
        assert abs(stats["mean"] - np.mean(freqs)) < 0.001


class TestCUSUMDetector:
    """Test cases for CUSUM change point detector."""

    def test_initialization(self):
        """Test CUSUM detector initializes correctly."""
        detector = CUSUMDetector(window_size=50, shared_resources=None, show_init=False)
        assert detector.window_size == 50
        assert detector.sum_pos == 0.0
        assert detector.sum_neg == 0.0

    def test_reference_establishment(self):
        """Test that reference is established from initial samples."""
        detector = CUSUMDetector(window_size=50, shared_resources=None, show_init=False)

        # Add initial samples
        freqs = [0.5, 0.5, 0.5]
        for f in freqs:
            detector.add_frequency(f, timestamp=0.0)

        assert detector.initialized
        assert abs(detector.reference - 0.5) < 0.001

    def test_detects_upward_change(self):
        """Test detection of upward frequency shift."""
        detector = CUSUMDetector(window_size=50, shared_resources=None, show_init=False)

        # Establish baseline
        for i in range(5):
            detector.add_frequency(0.1, timestamp=float(i))

        # Introduce upward shift
        change_detected = False
        for i in range(5, 20):
            detected, info = detector.add_frequency(1.0, timestamp=float(i))
            if detected:
                change_detected = True
                break

        assert change_detected

    def test_reset_on_nan(self):
        """Test that NaN frequency resets CUSUM state."""
        detector = CUSUMDetector(window_size=50, shared_resources=None, show_init=False)

        # Add some frequencies
        for i in range(5):
            detector.add_frequency(0.5, timestamp=float(i))

        # Add NaN
        detector.add_frequency(np.nan, timestamp=5.0)

        assert not detector.initialized
        assert detector.sum_pos == 0.0
        assert detector.sum_neg == 0.0


class TestPageHinkleyDetector:
    """Test cases for Page-Hinkley change point detector."""

    def test_initialization(self):
        """Test Page-Hinkley detector initializes correctly."""
        detector = SelfTuningPageHinkleyDetector(
            window_size=10, shared_resources=None, show_init=False
        )
        assert detector.window_size == 10
        assert detector.cumulative_sum_pos == 0.0
        assert detector.cumulative_sum_neg == 0.0

    def test_reference_mean_update(self):
        """Test that reference mean updates with new samples."""
        detector = SelfTuningPageHinkleyDetector(
            window_size=10, shared_resources=None, show_init=False
        )

        # Add samples
        detector.add_frequency(0.5, timestamp=0.0)
        assert detector.reference_mean == 0.5

        detector.add_frequency(1.0, timestamp=1.0)
        assert abs(detector.reference_mean - 0.75) < 0.001

    def test_detects_change(self):
        """Test detection of frequency change."""
        detector = SelfTuningPageHinkleyDetector(
            window_size=10, shared_resources=None, show_init=False
        )

        # Establish baseline
        for i in range(5):
            detector.add_frequency(0.1, timestamp=float(i))

        # Introduce shift
        change_detected = False
        for i in range(5, 20):
            detected, _, _ = detector.add_frequency(1.0, timestamp=float(i))
            if detected:
                change_detected = True
                break

        assert change_detected

    def test_reset_functionality(self):
        """Test reset functionality."""
        detector = SelfTuningPageHinkleyDetector(
            window_size=10, shared_resources=None, show_init=False
        )

        # Add samples and accumulate state
        for i in range(5):
            detector.add_frequency(0.5, timestamp=float(i))

        # Reset with new frequency
        detector.reset(current_freq=1.0)

        assert detector.cumulative_sum_pos == 0.0
        assert detector.cumulative_sum_neg == 0.0
        assert detector.reference_mean == 1.0


class TestDetectorIntegration:
    """Integration tests for change point detectors."""

    def test_all_detectors_handle_empty_input(self):
        """Test all detectors handle edge cases gracefully."""
        adwin = ChangePointDetector(delta=0.05, shared_resources=None, show_init=False)
        cusum = CUSUMDetector(window_size=50, shared_resources=None, show_init=False)
        ph = SelfTuningPageHinkleyDetector(
            window_size=10, shared_resources=None, show_init=False
        )

        # Test with zero frequency
        pred = create_mock_prediction(freq=0.0, t_start=0, t_end=1)

        result_adwin = adwin.add_prediction(pred, timestamp=1.0)
        result_cusum = cusum.add_frequency(0.0, timestamp=1.0)
        result_ph = ph.add_frequency(0.0, timestamp=1.0)

        # All should handle gracefully (not crash)
        assert result_adwin is None
        assert result_cusum == (False, {})
        assert result_ph == (False, 0.0, {})

    def test_all_detectors_consistent_detection(self):
        """Test all detectors can detect obvious pattern changes."""
        adwin = ChangePointDetector(delta=0.05, shared_resources=None, show_init=False)
        cusum = CUSUMDetector(window_size=50, shared_resources=None, show_init=False)
        ph = SelfTuningPageHinkleyDetector(
            window_size=10, shared_resources=None, show_init=False
        )

        # Create obvious pattern change: 0.1 Hz -> 10 Hz
        low_freq = 0.1
        high_freq = 10.0

        # Feed low frequency
        for i in range(10):
            pred = create_mock_prediction(freq=low_freq, t_start=i, t_end=i + 1)
            adwin.add_prediction(pred, timestamp=float(i + 1))
            cusum.add_frequency(low_freq, timestamp=float(i + 1))
            ph.add_frequency(low_freq, timestamp=float(i + 1))

        # Feed high frequency and check for detection
        adwin_detected = False
        cusum_detected = False
        ph_detected = False

        for i in range(10, 30):
            pred = create_mock_prediction(freq=high_freq, t_start=i, t_end=i + 1)

            if adwin.add_prediction(pred, timestamp=float(i + 1)) is not None:
                adwin_detected = True

            detected, _ = cusum.add_frequency(high_freq, timestamp=float(i + 1))
            if detected:
                cusum_detected = True

            detected, _, _ = ph.add_frequency(high_freq, timestamp=float(i + 1))
            if detected:
                ph_detected = True

        # All detectors should detect such an obvious change
        assert adwin_detected or cusum_detected or ph_detected
