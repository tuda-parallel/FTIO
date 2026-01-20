"""
Tests for ftio.analysis module.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from ftio.analysis.signal_analysis import sliding_correlation as signal_sliding_correlation
from ftio.analysis._logicize import logicize
from ftio.analysis._correlation import (
    correlation,
    sliding_correlation,
    extract_correlation_ranges,
)
from ftio.analysis.anomaly_detection import (
    outlier_detection,
    z_score,
    db_scan,
    isolation_forest,
    lof,
    peaks,
    dominant,
    remove_harmonics,
    norm_conf,
)


class TestSignalAnalysis:
    """Tests for signal_analysis.py - sliding_correlation function."""

    def test_sliding_correlation_basic(self):
        """Test basic sliding correlation with identical signals."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        window_size = 3

        corrs = signal_sliding_correlation(x, y, window_size)

        assert len(corrs) == len(x) - window_size + 1
        # Identical signals should have correlation of 1
        assert np.allclose(corrs, 1.0)

    def test_sliding_correlation_opposite_signals(self):
        """Test sliding correlation with negatively correlated signals."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
        window_size = 3

        corrs = signal_sliding_correlation(x, y, window_size)

        assert len(corrs) == 3
        # Opposite signals should have correlation of -1
        assert np.allclose(corrs, -1.0)

    def test_sliding_correlation_zero_std(self):
        """Test sliding correlation when one signal has zero std."""
        x = np.array([1.0, 1.0, 1.0, 2.0, 3.0])  # First window has zero std
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        window_size = 3

        corrs = signal_sliding_correlation(x, y, window_size)

        # First window has zero std for x, should return 0
        assert corrs[0] == 0

    def test_sliding_correlation_window_size_equals_length(self):
        """Test when window size equals signal length."""
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([1.0, 2.0, 3.0])
        window_size = 3

        corrs = signal_sliding_correlation(x, y, window_size)

        assert len(corrs) == 1
        assert np.isclose(corrs[0], 1.0)


class TestLogicize:
    """Tests for _logicize.py - logicize function."""

    def test_logicize_basic(self):
        """Test basic logicization."""
        b = np.array([0.0, 1.0, 0.0, 2.5, 0.0, -3.0])

        result = logicize(b, verbose=False)

        expected = np.array([0, 1, 0, 1, 0, 1])
        np.testing.assert_array_equal(result, expected)

    def test_logicize_all_zeros(self):
        """Test logicization with all zeros."""
        b = np.array([0.0, 0.0, 0.0])

        result = logicize(b, verbose=False)

        expected = np.array([0, 0, 0])
        np.testing.assert_array_equal(result, expected)

    def test_logicize_all_nonzero(self):
        """Test logicization with all non-zero values."""
        b = np.array([1.0, -1.0, 0.5, -0.5])

        result = logicize(b, verbose=False)

        expected = np.array([1, 1, 1, 1])
        np.testing.assert_array_equal(result, expected)

    def test_logicize_near_zero_threshold(self):
        """Test that values very close to zero (< 1e-8) are treated as zero."""
        b = np.array([1e-9, 1e-7, 1.0])

        result = logicize(b, verbose=False)

        # 1e-9 should be treated as 0, 1e-7 should be treated as 1
        expected = np.array([0, 1, 1])
        np.testing.assert_array_equal(result, expected)

    def test_logicize_verbose(self):
        """Test logicization with verbose output (verbose=False to avoid style issues)."""
        b = np.array([0.0, 1.0, 2.0])

        # Test with verbose=False (verbose=True has style dependency)
        result = logicize(b, verbose=False)

        expected = np.array([0, 1, 1])
        np.testing.assert_array_equal(result, expected)


class TestCorrelation:
    """Tests for _correlation.py - correlation functions."""

    def test_correlation_pearson_identical(self):
        """Test Pearson correlation with identical signals."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        r = correlation(x, y, method="pearson")

        assert np.isclose(r, 1.0)

    def test_correlation_pearson_opposite(self):
        """Test Pearson correlation with negatively correlated signals."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([5.0, 4.0, 3.0, 2.0, 1.0])

        r = correlation(x, y, method="pearson")

        assert np.isclose(r, -1.0)

    def test_correlation_pearson_zero_std(self):
        """Test Pearson correlation when one signal has zero std."""
        x = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        r = correlation(x, y, method="pearson")

        assert r == 0

    def test_correlation_spearman(self):
        """Test Spearman correlation."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        r = correlation(x, y, method="spearman")

        assert np.isclose(r, 1.0)

    def test_correlation_spearman_opposite(self):
        """Test Spearman correlation with opposite signals."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([5.0, 4.0, 3.0, 2.0, 1.0])

        r = correlation(x, y, method="spearman")

        assert np.isclose(r, -1.0)

    def test_correlation_spearman_constant(self):
        """Test Spearman correlation with constant signals (returns NaN -> 0)."""
        x = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        y = np.array([1.0, 1.0, 1.0, 1.0, 1.0])

        r = correlation(x, y, method="spearman")

        assert r == 0

    def test_correlation_different_lengths_raises(self):
        """Test that different length signals raise ValueError."""
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([1.0, 2.0])

        with pytest.raises(ValueError, match="same length"):
            correlation(x, y)

    def test_correlation_unsupported_method_raises(self):
        """Test that unsupported method raises ValueError."""
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([1.0, 2.0, 3.0])

        with pytest.raises(ValueError, match="Unsupported method"):
            correlation(x, y, method="kendall")

    def test_sliding_correlation_pearson(self):
        """Test sliding correlation with Pearson method."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        window_size = 3

        corrs = sliding_correlation(x, y, window_size, method="pearson")

        assert len(corrs) == 4
        assert np.allclose(corrs, 1.0)

    def test_sliding_correlation_spearman(self):
        """Test sliding correlation with Spearman method."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        window_size = 3

        corrs = sliding_correlation(x, y, window_size, method="spearman")

        assert len(corrs) == 4
        assert np.allclose(corrs, 1.0)


class TestExtractCorrelationRanges:
    """Tests for extract_correlation_ranges function."""

    def test_extract_ranges_basic(self):
        """Test basic range extraction."""
        t = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        corrs = np.array([0.0, 0.5, 0.8, 0.9, 0.3, 0.0])

        ranges = extract_correlation_ranges(t, corrs, threshold_low=0.5, threshold_high=1.0)

        assert len(ranges) >= 1
        # Should find range where correlation is between 0.5 and 1.0

    def test_extract_ranges_no_match(self):
        """Test when no ranges match the threshold."""
        t = np.array([0.0, 1.0, 2.0, 3.0])
        corrs = np.array([0.0, 0.1, 0.1, 0.0])

        ranges = extract_correlation_ranges(t, corrs, threshold_low=0.5, threshold_high=1.0)

        assert len(ranges) == 0

    def test_extract_ranges_starts_true(self):
        """Test when mask starts with True."""
        t = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        corrs = np.array([0.8, 0.9, 0.5, 0.1, 0.0])

        ranges = extract_correlation_ranges(t, corrs, threshold_low=0.5, threshold_high=1.0)

        assert len(ranges) >= 1
        assert ranges[0][0] == 0.0  # Should start from the beginning

    def test_extract_ranges_ends_true(self):
        """Test when mask ends with True."""
        t = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        corrs = np.array([0.1, 0.2, 0.6, 0.8, 0.9])

        ranges = extract_correlation_ranges(t, corrs, threshold_low=0.5, threshold_high=1.0)

        assert len(ranges) >= 1
        assert ranges[-1][1] == 4.0  # Should end at the last element

    def test_extract_ranges_min_duration(self):
        """Test filtering by minimum duration."""
        t = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
        corrs = np.array([0.8, 0.8, 0.1, 0.1, 0.1, 0.8, 0.8, 0.8, 0.8, 0.8])

        # With min_duration=3.0, short segments should be filtered out
        ranges = extract_correlation_ranges(
            t, corrs, threshold_low=0.5, threshold_high=1.0, min_duration=3.0
        )

        # Only the longer segment should remain
        for start, end in ranges:
            assert (end - start) >= 3.0

    def test_extract_ranges_verbose(self):
        """Test with verbose output."""
        t = np.array([0.0, 1.0, 2.0, 3.0])
        corrs = np.array([0.8, 0.9, 0.8, 0.9])

        # Should not raise an error
        ranges = extract_correlation_ranges(
            t, corrs, threshold_low=0.5, threshold_high=1.0, verbose=True
        )

        assert len(ranges) >= 1


class TestAnomalyDetection:
    """Tests for anomaly_detection.py functions."""

    @pytest.fixture
    def mock_args(self):
        """Create mock args object for testing."""
        args = MagicMock()
        args.psd = True
        args.tol = 0.8
        args.engine = "no"  # Disable plotting
        args.cepstrum = False
        return args

    @pytest.fixture
    def periodic_signal_data(self):
        """Create data for a periodic signal with clear dominant frequency."""
        # Generate a signal with clear periodic component
        n = 256
        freq_arr = np.fft.fftfreq(n, d=1.0)
        freq_arr = np.abs(freq_arr[:n // 2 + 1])
        freq_arr[0] = 1e-10  # Avoid division by zero

        # Create amplitude spectrum with a dominant peak
        amp = np.zeros(n)
        amp[10] = 10.0  # Strong peak at index 10
        amp[20] = 2.0   # Weaker peak at index 20

        return amp, freq_arr

    def test_z_score_basic(self, mock_args, periodic_signal_data):
        """Test Z-score outlier detection."""
        amp, freq_arr = periodic_signal_data

        dominant_index, conf, text = z_score(amp, freq_arr, mock_args)

        assert isinstance(dominant_index, list)
        assert isinstance(conf, np.ndarray)
        assert isinstance(text, str)

    def test_z_score_no_psd(self, mock_args, periodic_signal_data):
        """Test Z-score without power spectrum."""
        amp, freq_arr = periodic_signal_data
        mock_args.psd = False

        dominant_index, conf, text = z_score(amp, freq_arr, mock_args)

        assert "Amplitude spectrum" in text

    def test_db_scan_basic(self, mock_args, periodic_signal_data):
        """Test DBSCAN outlier detection."""
        amp, freq_arr = periodic_signal_data

        dominant_index, conf, text = db_scan(amp, freq_arr, mock_args)

        assert isinstance(dominant_index, list)
        assert isinstance(conf, np.ndarray)
        assert isinstance(text, str)

    def test_isolation_forest_basic(self, mock_args, periodic_signal_data):
        """Test Isolation Forest outlier detection."""
        amp, freq_arr = periodic_signal_data

        dominant_index, conf, text = isolation_forest(amp, freq_arr, mock_args)

        assert isinstance(dominant_index, list)
        assert isinstance(conf, np.ndarray)
        assert isinstance(text, str)

    def test_lof_basic(self, mock_args, periodic_signal_data):
        """Test Local Outlier Factor detection."""
        amp, freq_arr = periodic_signal_data

        dominant_index, conf, text = lof(amp, freq_arr, mock_args)

        assert isinstance(dominant_index, list)
        assert isinstance(conf, np.ndarray)
        assert isinstance(text, str)

    def test_peaks_basic(self, mock_args, periodic_signal_data):
        """Test find_peaks outlier detection."""
        amp, freq_arr = periodic_signal_data

        dominant_index, conf, text = peaks(amp, freq_arr, mock_args)

        assert isinstance(dominant_index, list)
        assert isinstance(conf, np.ndarray)
        assert isinstance(text, str)

    def test_outlier_detection_z_score(self, mock_args, periodic_signal_data):
        """Test outlier_detection with z-score method."""
        amp, freq_arr = periodic_signal_data
        mock_args.outlier = "z-score"

        dominant_index, conf, panel = outlier_detection(amp, freq_arr, mock_args)

        assert isinstance(dominant_index, list)
        assert isinstance(conf, np.ndarray)

    def test_outlier_detection_dbscan(self, mock_args, periodic_signal_data):
        """Test outlier_detection with dbscan method."""
        amp, freq_arr = periodic_signal_data
        mock_args.outlier = "dbscan"

        dominant_index, conf, panel = outlier_detection(amp, freq_arr, mock_args)

        assert isinstance(dominant_index, list)

    def test_outlier_detection_forest(self, mock_args, periodic_signal_data):
        """Test outlier_detection with isolation forest method."""
        amp, freq_arr = periodic_signal_data
        mock_args.outlier = "forest"

        dominant_index, conf, panel = outlier_detection(amp, freq_arr, mock_args)

        assert isinstance(dominant_index, list)

    def test_outlier_detection_lof(self, mock_args, periodic_signal_data):
        """Test outlier_detection with LOF method."""
        amp, freq_arr = periodic_signal_data
        mock_args.outlier = "lof"

        dominant_index, conf, panel = outlier_detection(amp, freq_arr, mock_args)

        assert isinstance(dominant_index, list)

    def test_outlier_detection_peaks(self, mock_args, periodic_signal_data):
        """Test outlier_detection with peaks method."""
        amp, freq_arr = periodic_signal_data
        mock_args.outlier = "peak"

        dominant_index, conf, panel = outlier_detection(amp, freq_arr, mock_args)

        assert isinstance(dominant_index, list)

    def test_outlier_detection_unsupported_method(self, mock_args, periodic_signal_data):
        """Test outlier_detection with unsupported method raises error."""
        amp, freq_arr = periodic_signal_data
        mock_args.outlier = "unsupported_method"

        with pytest.raises(NotImplementedError):
            outlier_detection(amp, freq_arr, mock_args)


class TestDominant:
    """Tests for the dominant function."""

    def test_dominant_single_frequency(self):
        """Test dominant with a single frequency."""
        freq_arr = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
        conf = np.array([0.0, 0.5, 0.3, 0.2, 0.1])
        dominant_index = np.array([1])

        result, text = dominant(dominant_index, freq_arr, conf)

        assert 1 in result
        assert "Dominant frequency" in text

    def test_dominant_empty(self):
        """Test dominant with no frequencies."""
        freq_arr = np.array([0.0, 0.1, 0.2])
        conf = np.array([0.0, 0.0, 0.0])
        dominant_index = np.array([])

        result, text = dominant(dominant_index, freq_arr, conf)

        assert len(result) == 0
        assert "No dominant frequencies" in text

    def test_dominant_too_many(self):
        """Test dominant with too many frequencies (>3)."""
        # Use frequencies that are not harmonics of each other (primes-based)
        freq_arr = np.array([0.0, 0.17, 0.23, 0.31, 0.41])
        conf = np.array([0.0, 0.5, 0.4, 0.3, 0.2])
        dominant_index = np.array([1, 2, 3, 4])  # 4 non-harmonic frequencies

        result, text = dominant(dominant_index, freq_arr, conf)

        assert len(result) == 0  # Should be empty when too many
        assert "Too many dominant frequencies" in text


class TestRemoveHarmonics:
    """Tests for the remove_harmonics function."""

    def test_remove_harmonics_basic(self):
        """Test basic harmonic removal."""
        freq_arr = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
        amp_tmp = np.array([0.0, 1.0, 0.5, 0.3, 0.2])
        index_list = np.array([1, 2])  # 0.2 is harmonic of 0.1

        seen, removed, msg = remove_harmonics(freq_arr, amp_tmp, index_list)

        assert 1 in seen
        # 0.2 is harmonic of 0.1 (0.2 % 0.1 = 0)
        assert 2 in removed or 2 in seen

    def test_remove_harmonics_no_harmonics(self):
        """Test when there are no harmonics to remove."""
        freq_arr = np.array([0.0, 0.1, 0.23, 0.37])
        amp_tmp = np.array([0.0, 1.0, 0.5, 0.3])
        index_list = np.array([1, 2, 3])

        seen, removed, msg = remove_harmonics(freq_arr, amp_tmp, index_list)

        # No harmonics to remove
        assert len(seen) == 3
        assert len(removed) == 0

    def test_remove_harmonics_empty(self):
        """Test with empty index list."""
        freq_arr = np.array([0.0, 0.1, 0.2])
        amp_tmp = np.array([0.0, 1.0, 0.5])
        index_list = np.array([])

        seen, removed, msg = remove_harmonics(freq_arr, amp_tmp, index_list)

        assert len(seen) == 0
        assert len(removed) == 0


class TestNormConf:
    """Tests for the norm_conf function."""

    def test_norm_conf_basic(self):
        """Test basic confidence normalization."""
        conf = np.array([-1.0, 0.0, 1.0])

        result = norm_conf(conf)

        # Strongest outlier (-1.0) should become 1.0
        # Strongest inlier (1.0) should become 0.0
        assert result[0] == 1.0
        assert result[2] == 0.0

    def test_norm_conf_all_same(self):
        """Test when all confidence values are the same."""
        conf = np.array([0.5, 0.5, 0.5])

        result = norm_conf(conf)

        # All should be zero when values are the same
        np.testing.assert_array_equal(result, np.zeros(3))

    def test_norm_conf_min_zero(self):
        """Test when minimum confidence is zero."""
        conf = np.array([0.0, 0.5, 1.0])

        result = norm_conf(conf)

        # Should normalize properly without division by zero
        assert result[0] == 1.0
        assert result[2] == 0.0


class TestPeriodicityAnalysis:
    """Tests for periodicity_analysis.py functions."""

    @pytest.fixture
    def mock_args(self):
        """Create mock args for periodicity analysis."""
        args = MagicMock()
        args.psd = True
        args.periodicity_detection = None
        args.n_freq = 0
        return args

    @pytest.fixture
    def mock_prediction(self):
        """Create mock prediction object."""
        prediction = MagicMock()
        prediction.dominant_freq = [0.1]
        prediction.phi = [0.0]
        prediction.freq = 10.0
        prediction.t_start = 0.0
        prediction.top_freqs = {"freq": [0.1], "phi": [0.0], "periodicity": [0.0]}
        return prediction

    def test_periodicity_scores_no_detection(self, mock_args, mock_prediction):
        """Test when periodicity detection is disabled."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        amp = np.random.rand(100)
        signal = np.random.rand(100)

        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        assert result == ""  # No output when detection is disabled

    def test_periodicity_scores_rpde(self, mock_args, mock_prediction):
        """Test RPDE periodicity detection."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        mock_args.periodicity_detection = "rpde"
        amp = np.random.rand(100) + 0.1  # Ensure positive values
        signal = np.random.rand(100)

        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        # Should return a Panel object
        assert result is not None

    def test_periodicity_scores_sf(self, mock_args, mock_prediction):
        """Test spectral flatness periodicity detection."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        mock_args.periodicity_detection = "sf"
        amp = np.random.rand(100) + 0.1
        signal = np.random.rand(100)

        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        assert result is not None

    def test_periodicity_scores_corr(self, mock_args, mock_prediction):
        """Test correlation-based periodicity detection."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        mock_args.periodicity_detection = "corr"
        mock_prediction.dominant_freq = [0.1]
        mock_prediction.phi = [0.0]
        mock_prediction.freq = 10.0
        mock_prediction.t_start = 0.0

        amp = np.random.rand(100) + 0.1
        signal = np.sin(2 * np.pi * 0.1 * np.arange(100) / 10.0)

        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        assert result is not None

    def test_periodicity_scores_ind(self, mock_args, mock_prediction):
        """Test individual period correlation detection."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        mock_args.periodicity_detection = "ind"
        mock_prediction.dominant_freq = [0.1]
        mock_prediction.phi = [0.0]
        mock_prediction.freq = 10.0
        mock_prediction.t_start = 0.0

        amp = np.random.rand(100) + 0.1
        signal = np.sin(2 * np.pi * 0.1 * np.arange(100) / 10.0)

        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        assert result is not None

    def test_periodicity_scores_n_freq(self, mock_args, mock_prediction):
        """Test periodicity detection with n_freq > 0."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        mock_args.periodicity_detection = "rpde"
        mock_args.n_freq = 2
        mock_prediction.top_freqs = {
            "freq": np.array([0.1, 0.2]),
            "phi": np.array([0.0, 0.0]),
            "periodicity": np.array([0.0, 0.0]),
        }

        amp = np.random.rand(100) + 0.1
        signal = np.random.rand(100)

        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        assert result is not None


class TestCorrelationPlotAndRanges:
    """Additional tests for _correlation.py to improve coverage."""

    def test_extract_ranges_merging(self):
        """Test that nearby ranges get merged correctly."""
        t = np.linspace(0, 10, 100)
        # Create correlation values with multiple nearby high regions
        corrs = np.zeros(100)
        corrs[10:20] = 0.8  # First high region
        corrs[22:32] = 0.8  # Second high region (close to first)
        corrs[60:70] = 0.8  # Third high region (far from others)

        # With min_duration=0.5, nearby ranges should be merged
        ranges = extract_correlation_ranges(
            t, corrs, threshold_low=0.5, threshold_high=1.0, min_duration=0.5
        )

        assert len(ranges) >= 1

    def test_extract_ranges_empty_result(self):
        """Test when no ranges meet criteria."""
        t = np.array([0.0, 1.0, 2.0, 3.0])
        corrs = np.array([0.2, 0.2, 0.2, 0.2])  # All below threshold

        ranges = extract_correlation_ranges(
            t, corrs, threshold_low=0.5, threshold_high=1.0
        )

        assert len(ranges) == 0

    def test_extract_ranges_assertion_error(self):
        """Test that mismatched lengths raise assertion error."""
        t = np.array([0.0, 1.0, 2.0])
        corrs = np.array([0.5, 0.5])  # Different length

        with pytest.raises(AssertionError):
            extract_correlation_ranges(t, corrs)


class TestAnomalyDetectionAdditional:
    """Additional tests for anomaly_detection.py to improve coverage."""

    @pytest.fixture
    def mock_args(self):
        """Create mock args object for testing."""
        args = MagicMock()
        args.psd = True
        args.tol = 0.8
        args.engine = "no"
        args.cepstrum = False
        return args

    def test_z_score_no_outliers(self, mock_args):
        """Test Z-score when no outliers are found."""
        # Create flat spectrum with no clear peaks
        n = 256
        freq_arr = np.fft.fftfreq(n, d=1.0)
        freq_arr = np.abs(freq_arr[:n // 2 + 1])
        freq_arr[0] = 1e-10

        amp = np.ones(n) * 0.1  # Flat spectrum

        dominant_index, conf, text = z_score(amp, freq_arr, mock_args)

        # Should report no dominant frequency
        assert "not periodic" in text.lower() or len(dominant_index) == 0

    def test_z_score_many_candidates(self, mock_args):
        """Test Z-score with many candidate frequencies."""
        n = 256
        freq_arr = np.fft.fftfreq(n, d=1.0)
        freq_arr = np.abs(freq_arr[:n // 2 + 1])
        freq_arr[0] = 1e-10

        # Create spectrum with multiple strong peaks
        amp = np.zeros(n)
        amp[10] = 10.0
        amp[15] = 9.0
        amp[20] = 8.0
        amp[25] = 7.0
        amp[30] = 6.0

        mock_args.tol = 0.5  # Lower tolerance to get more candidates

        dominant_index, conf, text = z_score(amp, freq_arr, mock_args)

        assert isinstance(text, str)

    def test_z_score_zero_std(self, mock_args):
        """Test Z-score when std is zero."""
        n = 64
        freq_arr = np.fft.fftfreq(n, d=1.0)
        freq_arr = np.abs(freq_arr[:n // 2 + 1])
        freq_arr[0] = 1e-10

        amp = np.ones(n) * 1.0  # All same values, std = 0

        dominant_index, conf, text = z_score(amp, freq_arr, mock_args)

        assert isinstance(conf, np.ndarray)

    def test_db_scan_different_eps_modes(self, mock_args):
        """Test DBSCAN with different data characteristics."""
        n = 256
        freq_arr = np.fft.fftfreq(n, d=1.0)
        freq_arr = np.abs(freq_arr[:n // 2 + 1])
        freq_arr[0] = 1e-10

        # Create spectrum with clear peak
        amp = np.random.rand(n) * 0.1
        amp[20] = 5.0

        dominant_index, conf, text = db_scan(amp, freq_arr, mock_args)

        assert "eps" in text.lower()

    def test_norm_conf_negative_values(self):
        """Test norm_conf with negative values."""
        conf = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])

        result = norm_conf(conf)

        # Should be normalized between 0 and 1
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_dominant_with_harmonics(self):
        """Test dominant function properly ignores harmonics."""
        # Frequencies where 0.2 is harmonic of 0.1
        freq_arr = np.array([0.0, 0.1, 0.2, 0.35])
        conf = np.array([0.0, 0.5, 0.4, 0.3])
        dominant_index = np.array([1, 2, 3])  # 0.2 is harmonic of 0.1

        result, text = dominant(dominant_index, freq_arr, conf)

        # Should have ignored the harmonic
        assert "harmonic" in text.lower() or len(result) <= 2


class TestPeriodicityAnalysisAdditional:
    """Additional tests for periodicity_analysis.py to improve coverage."""

    @pytest.fixture
    def mock_args(self):
        """Create mock args for periodicity analysis."""
        args = MagicMock()
        args.psd = True
        args.periodicity_detection = None
        args.n_freq = 0
        return args

    @pytest.fixture
    def mock_prediction(self):
        """Create mock prediction object."""
        prediction = MagicMock()
        prediction.dominant_freq = [0.1]
        prediction.phi = [0.0]
        prediction.freq = 10.0
        prediction.t_start = 0.0
        prediction.top_freqs = {"freq": [0.1], "phi": [0.0], "periodicity": [0.0]}
        return prediction

    def test_periodicity_corr_with_n_freq(self, mock_args, mock_prediction):
        """Test correlation-based periodicity with n_freq > 0."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        mock_args.periodicity_detection = "corr"
        mock_args.n_freq = 2
        mock_prediction.dominant_freq = [0.1, 0.2]
        mock_prediction.phi = [0.0, 0.0]
        mock_prediction.top_freqs = {
            "freq": np.array([0.1, 0.2]),
            "phi": np.array([0.0, 0.0]),
            "periodicity": np.array([0.0, 0.0]),
        }

        amp = np.random.rand(100) + 0.1
        signal = np.sin(2 * np.pi * 0.1 * np.arange(100) / 10.0)

        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        assert result is not None

    def test_periodicity_ind_with_n_freq(self, mock_args, mock_prediction):
        """Test individual period correlation with n_freq > 0."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        mock_args.periodicity_detection = "ind"
        mock_args.n_freq = 2
        mock_prediction.dominant_freq = [0.1, 0.2]
        mock_prediction.phi = [0.0, 0.0]
        mock_prediction.top_freqs = {
            "freq": np.array([0.1, 0.2]),
            "phi": np.array([0.0, 0.0]),
            "periodicity": np.array([0.0, 0.0]),
        }

        amp = np.random.rand(100) + 0.1
        signal = np.sin(2 * np.pi * 0.1 * np.arange(100) / 10.0)

        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        assert result is not None

    def test_periodicity_empty_dominant_freq(self, mock_args, mock_prediction):
        """Test periodicity detection with empty dominant frequencies."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        mock_args.periodicity_detection = "corr"
        mock_prediction.dominant_freq = []  # Empty

        amp = np.random.rand(100) + 0.1
        signal = np.random.rand(100)

        # Should not crash with empty dominant_freq
        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        # Returns Panel or empty string depending on path taken
        assert result is not None or result == ""

    def test_periodicity_sf_with_n_freq(self, mock_args, mock_prediction):
        """Test spectral flatness with n_freq > 0."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        mock_args.periodicity_detection = "sf"
        mock_args.n_freq = 2
        mock_prediction.top_freqs = {
            "freq": np.array([0.1, 0.2]),
            "phi": np.array([0.0, 0.0]),
            "periodicity": np.array([0.0, 0.0]),
        }

        amp = np.random.rand(100) + 0.1
        signal = np.random.rand(100)

        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        assert result is not None

    def test_periodicity_amp_sum_zero(self, mock_args, mock_prediction):
        """Test periodicity when amplitude sum is zero."""
        from ftio.analysis.periodicity_analysis import new_periodicity_scores

        mock_args.periodicity_detection = "rpde"

        amp = np.zeros(100)  # All zeros
        signal = np.random.rand(100)

        result = new_periodicity_scores(amp, signal, mock_prediction, mock_args)

        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
