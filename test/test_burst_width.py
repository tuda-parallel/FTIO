"""
Tests for burst-width (duty-cycle) estimation.

Author: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Version: 0.0.8
Date: Jun 2026

Licensed under the BSD 3-Clause License.
"""

import numpy as np
import pytest

from ftio.freq.duty_cycle import _min_contiguous_window, estimate_burst_widths
from ftio.freq.prediction import Prediction
from ftio.parse.args import parse_args

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_periodic_signal(fs, f_dom, duty, n_periods=10, amp=1.0, noise=0.0, rng=None):
    """Rectangular burst signal with known duty cycle."""
    if rng is None:
        rng = np.random.default_rng(0)
    T = 1.0 / f_dom
    duration = n_periods * T
    t = np.arange(0, duration, 1.0 / fs)
    signal = np.zeros(len(t))
    for k in range(n_periods):
        t0 = k * T
        t1 = t0 + duty * T
        mask = (t >= t0) & (t < t1)
        signal[mask] = amp
    if noise > 0:
        signal += rng.normal(0, noise, len(t))
    signal = np.clip(signal, 0, None)
    return t, signal


def _make_prediction(fs, f_dom, t_start=0.0):
    p = Prediction("dft")
    p.freq = float(fs)
    p.dominant_freq = np.array([f_dom])
    p.conf = np.array([1.0])
    p.amp = np.array([1.0])
    p.phi = np.array([0.0])
    p.t_start = t_start
    p.t_end = t_start + 10.0
    p.n_samples = int(fs * 10)
    return p


# ── unit tests: _min_contiguous_window ───────────────────────────────────────


class TestMinContiguousWindow:
    def test_single_spike(self):
        power = np.array([0.0, 0.0, 1.0, 0.0, 0.0])
        w, left = _min_contiguous_window(power, 1.0)
        assert w == 1
        assert left == 2

    def test_uniform_signal(self):
        power = np.ones(10)
        w, left = _min_contiguous_window(power, 0.5)
        assert w == 5

    def test_two_equal_spikes(self):
        power = np.array([0.0, 1.0, 0.0, 0.0, 1.0, 0.0])
        # 95% of energy needs both spikes → window spans from index 1 to 4
        w, left = _min_contiguous_window(power, 0.95)
        assert left == 1
        assert left + w - 1 == 4

    def test_zero_signal_returns_zero_width(self):
        power = np.zeros(10)
        w, left = _min_contiguous_window(power, 0.95)
        assert w == 0

    def test_full_fraction(self):
        power = np.array([0.1, 0.5, 2.0, 0.5, 0.1])
        w, _ = _min_contiguous_window(power, 1.0)
        assert w == len(power)


# ── unit tests: estimate_burst_widths ────────────────────────────────────────


class TestEstimateBurstWidths:
    def test_known_duty_cycle(self):
        fs, f_dom, duty = 200, 0.5, 0.3
        t, signal = _make_periodic_signal(fs, f_dom, duty, n_periods=10)
        pred = _make_prediction(fs, f_dom, t_start=t[0])
        bws = estimate_burst_widths(signal, pred, energy_fraction=0.95)
        assert len(bws) == 10
        # median should be close to true burst width (duty / f_dom)
        expected = duty / f_dom
        assert abs(np.median(bws) - expected) < 0.10 * expected

    def test_duty_cycle_property(self):
        fs, f_dom, duty = 200, 0.5, 0.4
        t, signal = _make_periodic_signal(fs, f_dom, duty, n_periods=8)
        pred = _make_prediction(fs, f_dom, t_start=t[0])
        pred.burst_widths = estimate_burst_widths(signal, pred, energy_fraction=0.95)
        assert not np.isnan(pred.duty_cycle)
        assert abs(pred.duty_cycle - duty) < 0.08

    def test_no_dominant_freq(self):
        pred = Prediction("dft")
        pred.freq = 100.0
        pred.dominant_freq = np.array([])
        bws = estimate_burst_widths(np.ones(1000), pred)
        assert len(bws) == 0

    def test_signal_shorter_than_period(self):
        fs, f_dom = 100, 0.1  # T = 10s, signal = 5s
        signal = np.ones(int(fs * 5))
        pred = _make_prediction(fs, f_dom)
        bws = estimate_burst_widths(signal, pred)
        assert len(bws) == 0

    def test_min_max_properties(self):
        fs, f_dom = 200, 1.0
        rng = np.random.default_rng(7)
        t, signal = _make_periodic_signal(
            fs, f_dom, duty=0.3, n_periods=12, noise=0.02, rng=rng
        )
        pred = _make_prediction(fs, f_dom, t_start=t[0])
        pred.burst_widths = estimate_burst_widths(signal, pred)
        assert pred.burst_width_min <= pred.burst_width_median <= pred.burst_width_max

    def test_wider_duty_cycle_gives_wider_estimate(self):
        fs, f_dom = 200, 1.0
        t, sig_narrow = _make_periodic_signal(fs, f_dom, duty=0.2, n_periods=10)
        _, sig_wide = _make_periodic_signal(fs, f_dom, duty=0.6, n_periods=10)
        pred = _make_prediction(fs, f_dom, t_start=t[0])
        bw_narrow = np.median(estimate_burst_widths(sig_narrow, pred))
        bw_wide = np.median(estimate_burst_widths(sig_wide, pred))
        assert bw_narrow < bw_wide


# ── integration tests: --burst_width flag through each workflow ───────────────


def _base_args(transformation):
    return parse_args(["-tr", transformation, "-e", "no", "--burst_width"], "ftio")


class TestWorkflowIntegration:
    def _signal(self, fs=200, f_dom=1.0, duty=0.3, n_periods=10):
        t, sig = _make_periodic_signal(fs, f_dom, duty, n_periods)
        return t, sig

    def test_dft_workflow(self):
        from ftio.freq._dft_workflow import ftio_dft

        t, sig = self._signal()
        args = _base_args("dft")
        args.freq = 200
        pred, _ = ftio_dft(args, sig, t)
        assert len(pred.burst_widths) > 0
        assert not np.isnan(pred.burst_width_median)
        assert not np.isnan(pred.duty_cycle)

    def test_stft_workflow(self):
        from ftio.freq._stft_workflow import ftio_stft

        t, sig = self._signal()
        args = _base_args("stft")
        args.freq = 200
        pred, _ = ftio_stft(args, sig, t)
        assert len(pred.burst_widths) > 0

    def test_astft_workflow(self):
        pytest.importorskip("tftb", reason="tftb not installed")
        from ftio.freq._astft_workflow import ftio_astft

        t, sig = self._signal(f_dom=0.5, n_periods=6)
        args = _base_args("astft")
        args.freq = 200
        args.stft_window = "0"
        args.tfpf = 0
        pred, _ = ftio_astft(args, sig, t, total_bytes=0, ranks=1)
        # ASTFT may find no components on simple synthetic signals — just check no crash
        assert isinstance(pred.burst_widths, np.ndarray)

    def test_burst_width_off_by_default(self):
        from ftio.freq._dft_workflow import ftio_dft

        t, sig = self._signal()
        args = parse_args(["-tr", "dft", "-e", "no"], "ftio")
        args.freq = 200
        pred, _ = ftio_dft(args, sig, t)
        assert len(pred.burst_widths) == 0
