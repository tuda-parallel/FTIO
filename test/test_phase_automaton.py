"""
Test: PhaseAutomaton — state-machine modelling of I/O phases.

Scenario
--------
An application performs 12 I/O bursts and switches behaviour after the 6th:

  Phase A (bursts 1-6):  period =  5 s  → freq ≈ 0.200 Hz
  Phase B (bursts 7-12): period = 15 s  → freq ≈ 0.067 Hz

Expected automaton:
  State 0  (freq ≈ 0.20 Hz)  entered at start
  State 1  (freq ≈ 0.07 Hz)  entered when detector fires
  1 transition between State 0 and State 1

The multi-rank test shows that different rank configurations produce
separate automata that can be compared.

Author: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Version: 0.0.8
Date: May 2026

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from __future__ import annotations

import glob

import numpy as np
import pytest

from ftio.cli.ftio_core import core
from ftio.freq.prediction import Prediction
from ftio.parse.args import parse_args
from ftio.prediction.phase_automaton import PhaseAutomaton

# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


def _mock_prediction(
    freq: float,
    t_start: float,
    t_end: float,
    conf: float = 0.95,
    ranks: int = 1,
) -> Prediction:
    """Create a Prediction with a single known dominant frequency."""
    pred = Prediction(transformation="dft", t_start=t_start, t_end=t_end, ranks=ranks)
    pred.dominant_freq = np.array([freq])
    pred.conf = np.array([conf])
    pred.amp = np.array([1.0])
    return pred


def _generate_periodic_trace(
    phases: list[tuple[int, float, float, float]],
    dt: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    """
    Build a bandwidth time series from phase specifications.

    phases: list of (n_bursts, period_s, burst_dur_s, bandwidth)
    Returns: (time_arr, bandwidth_arr, burst_end_times)

    Each burst emits `bandwidth` for `burst_dur_s` seconds, then silence
    until the next burst start.
    """
    t_list: list[float] = []
    b_list: list[float] = []
    burst_ends: list[float] = []
    cur = 0.0

    for n_bursts, period, burst_dur, bw in phases:
        for _ in range(n_bursts):
            # high-bandwidth burst
            t_burst_end = cur + burst_dur
            while cur < t_burst_end - dt / 2:
                t_list.append(cur)
                b_list.append(bw)
                cur += dt
            burst_ends.append(cur)
            # silence until next burst
            t_period_end = burst_ends[-1] + (period - burst_dur)
            while cur < t_period_end - dt / 2:
                t_list.append(cur)
                b_list.append(0.0)
                cur += dt

    return np.array(t_list), np.array(b_list), burst_ends


def _analyze_windows(
    time_arr: np.ndarray,
    bw_arr: np.ndarray,
    burst_ends: list[float],
    window: float = 30.0,
    ranks: int = 1,
    min_samples: int = 20,
) -> list[Prediction]:
    """
    Run FTIO on a sliding window ending at each burst end time.
    Returns only non-empty predictions.
    """
    args = parse_args(["-e", "no"], "ftio")
    predictions: list[Prediction] = []
    for t_end in burst_ends:
        t_start = max(0.0, t_end - window)
        mask = (time_arr >= t_start) & (time_arr <= t_end)
        if mask.sum() < min_samples:
            continue
        sim = {
            "time": time_arr[mask],
            "bandwidth": bw_arr[mask],
            "total_bytes": 1,
            "ranks": ranks,
        }
        pred, _ = core(sim, args)
        if not pred.is_empty():
            predictions.append(pred)
    return predictions


# ──────────────────────────────────────────────────────────────────────
# Tests — statistical detectors (mock predictions)
# ──────────────────────────────────────────────────────────────────────


def test_phase_automaton_mock_cusum():
    """
    Unit test with hand-crafted predictions (no real FTIO analysis).

    Feed 5 predictions at 0.20 Hz then 5 at 0.05 Hz.
    CUSUM should detect exactly one transition.
    """
    phase_a = [_mock_prediction(0.20, t * 5.0, (t + 1) * 5.0) for t in range(5)]
    phase_b = [
        _mock_prediction(0.05, 25.0 + t * 20.0, 25.0 + (t + 1) * 20.0) for t in range(5)
    ]

    automaton = PhaseAutomaton(method="cusum")
    automaton.build(phase_a + phase_b)
    automaton.print_summary()

    assert (
        len(automaton.states) == 2
    ), f"Expected 2 states, got {len(automaton.states)}: {automaton.states}"
    assert (
        len(automaton.transitions) == 1
    ), f"Expected 1 transition, got {len(automaton.transitions)}"
    # State 0: phase A (high frequency)
    assert np.isclose(automaton.states[0].dominant_freq, 0.20, rtol=0.1)
    # State 1: phase B (lower frequency)
    assert np.isclose(automaton.states[1].dominant_freq, 0.05, rtol=0.1)
    # Transition fired after the phase-A predictions
    assert automaton.transitions[0].from_state == 0
    assert automaton.transitions[0].to_state == 1


def test_phase_automaton_mock_ph():
    """Same scenario with the Page-Hinkley detector."""
    phase_a = [_mock_prediction(0.20, t * 5.0, (t + 1) * 5.0) for t in range(6)]
    phase_b = [
        _mock_prediction(0.05, 30.0 + t * 20.0, 30.0 + (t + 1) * 20.0) for t in range(6)
    ]

    automaton = PhaseAutomaton(method="ph")
    automaton.build(phase_a + phase_b)
    automaton.print_summary()

    assert len(automaton.states) >= 2
    assert len(automaton.transitions) >= 1
    # First state has higher freq than the last
    assert automaton.states[0].dominant_freq > automaton.states[-1].dominant_freq


def test_phase_automaton_mock_ksigma():
    """
    k-sigma detector: two phases separated by 4x frequency change.

    With k=3 and sigma_rel_floor=0.02, each new phase observation must lie
    more than 3 effective-sigma away from the current phase mean.
    A 4x ratio (0.20 → 0.05 Hz) gives z >> 3 on the first sample from
    Phase B, so exactly one transition is expected.
    """
    phase_a = [_mock_prediction(0.20, t * 5.0, (t + 1) * 5.0) for t in range(6)]
    phase_b = [
        _mock_prediction(0.05, 30.0 + t * 20.0, 30.0 + (t + 1) * 20.0) for t in range(6)
    ]

    automaton = PhaseAutomaton(method="ksigma")
    automaton.build(phase_a + phase_b)
    automaton.print_summary()

    assert len(automaton.states) >= 2
    assert len(automaton.transitions) >= 1
    assert automaton.states[0].dominant_freq > automaton.states[-1].dominant_freq
    assert automaton.transitions[0].cause == "frequency"


def test_phase_automaton_ksigma_no_false_alarm():
    """
    k-sigma must not fire on within-phase noise.

    Phase A: 12 noisy predictions centred on 0.20 Hz with ±5 % jitter.
    Expected result: no transitions (1 state only).
    """
    rng = np.random.default_rng(0)
    freqs = 0.20 + rng.uniform(-0.01, 0.01, size=12)
    stream = [
        _mock_prediction(float(f), t * 5.0, (t + 1) * 5.0) for t, f in enumerate(freqs)
    ]

    aut = PhaseAutomaton(method="ksigma", rank_changes_trigger=False)
    aut.build(stream)
    aut.print_summary()

    assert len(aut.states) == 1, (
        f"k-sigma fired on within-phase noise — got {len(aut.states)} states, "
        f"{len(aut.transitions)} transitions"
    )
    assert len(aut.transitions) == 0


def test_phase_automaton_ksigma_detects_shift():
    """
    k-sigma detects a genuine 30 % upward shift despite within-phase noise.

    Phase A: 10 predictions at 0.20 ± 5 %  → establishes σ ≈ 0.006 Hz
    Phase B: 10 predictions at 0.26 ± 5 %  → z ≈ 10 >> k=3 → fires
    """
    rng = np.random.default_rng(42)

    def _noisy(freq, n, t0, period=5.0):
        raw = freq + rng.uniform(-0.05 * freq, 0.05 * freq, size=n)
        return [
            _mock_prediction(float(f), t0 + i * period, t0 + (i + 1) * period)
            for i, f in enumerate(raw)
        ]

    stream = _noisy(0.20, 10, t0=0.0) + _noisy(0.26, 10, t0=50.0)

    aut = PhaseAutomaton(method="ksigma", rank_changes_trigger=False)
    aut.build(stream)
    aut.print_summary()

    assert (
        len(aut.states) >= 2
    ), "k-sigma should detect the 30 % shift from Phase A to Phase B"
    assert len(aut.transitions) >= 1


def test_phase_automaton_mock_adwin():
    """
    ADWIN detector: requires a large frequency ratio to pass the Hoeffding bound
    with few samples.  With only ~6 observations per phase the bound is wide
    (~1.5 Hz at delta=0.05 and n_harmonic≈1.4), so we use 5.0 Hz vs 0.05 Hz
    (100:1 ratio, diff=4.95 Hz) to guarantee detection.
    """
    phase_a = [_mock_prediction(5.0, t * 0.2, (t + 1) * 0.2) for t in range(6)]
    phase_b = [
        _mock_prediction(0.05, 1.2 + t * 20.0, 1.2 + (t + 1) * 20.0) for t in range(6)
    ]

    automaton = PhaseAutomaton(method="adwin")
    automaton.build(phase_a + phase_b)
    automaton.print_summary()

    assert len(automaton.states) >= 2
    assert len(automaton.transitions) >= 1
    assert automaton.states[0].dominant_freq > automaton.states[-1].dominant_freq


# ──────────────────────────────────────────────────────────────────────
# Tests — non-statistical trigger mechanisms
# ──────────────────────────────────────────────────────────────────────


def test_phase_automaton_rank_change_trigger():
    """
    Rank change creates a new state even with identical frequency.

    Same dominant freq (0.20 Hz) but ranks change 4 → 8.
    With method=None (no statistical detector), only the rank-change
    trigger is active — it must fire exactly once.
    """
    stream = [
        _mock_prediction(0.20, t * 5.0, (t + 1) * 5.0, ranks=4) for t in range(4)
    ] + [
        _mock_prediction(0.20, 20.0 + t * 5.0, 20.0 + (t + 1) * 5.0, ranks=8)
        for t in range(4)
    ]

    aut = PhaseAutomaton(method=None, rank_changes_trigger=True)
    aut.build(stream)
    aut.print_summary()

    assert len(aut.states) == 2, f"Expected 2 states (rank change), got {len(aut.states)}"
    assert len(aut.transitions) == 1
    assert aut.transitions[0].cause == "rank_change"
    assert aut.states[0].ranks == 4
    assert aut.states[1].ranks == 8


def test_phase_automaton_period_ratio():
    """
    Period-ratio threshold triggers a transition without a statistical detector.

    0.20 Hz → 0.05 Hz: ratio = 0.20/0.05 = 4.0 > 1.5 → fires on the first
    prediction from the new phase (no warm-up samples needed).
    """
    stream = [_mock_prediction(0.20, t * 5.0, (t + 1) * 5.0) for t in range(3)] + [
        _mock_prediction(0.05, 15.0 + t * 20.0, 15.0 + (t + 1) * 20.0) for t in range(3)
    ]

    aut = PhaseAutomaton(
        method=None, period_ratio_threshold=1.5, rank_changes_trigger=False
    )
    aut.build(stream)
    aut.print_summary()

    assert len(aut.transitions) >= 1, "period-ratio should fire at least once"
    assert aut.transitions[0].cause == "period_ratio"


def test_phase_automaton_cause_field():
    """Transition cause is correctly labelled for each trigger type."""
    # rank_change
    stream_rank = [
        _mock_prediction(0.20, t * 5.0, (t + 1) * 5.0, ranks=1) for t in range(3)
    ] + [
        _mock_prediction(0.20, 15.0 + t * 5.0, 15.0 + (t + 1) * 5.0, ranks=2)
        for t in range(3)
    ]
    aut_rank = PhaseAutomaton(method=None, rank_changes_trigger=True)
    aut_rank.build(stream_rank)
    assert any(t.cause == "rank_change" for t in aut_rank.transitions)

    # period_ratio
    stream_ratio = [_mock_prediction(0.20, t * 5.0, (t + 1) * 5.0) for t in range(3)] + [
        _mock_prediction(0.05, 15.0 + t * 20.0, 15.0 + (t + 1) * 20.0) for t in range(3)
    ]
    aut_ratio = PhaseAutomaton(
        method=None, period_ratio_threshold=1.5, rank_changes_trigger=False
    )
    aut_ratio.build(stream_ratio)
    assert any(t.cause == "period_ratio" for t in aut_ratio.transitions)

    # frequency (CUSUM)
    stream_cusum = [_mock_prediction(0.20, t * 5.0, (t + 1) * 5.0) for t in range(5)] + [
        _mock_prediction(0.05, 25.0 + t * 20.0, 25.0 + (t + 1) * 20.0) for t in range(5)
    ]
    aut_cusum = PhaseAutomaton(
        method="cusum", rank_changes_trigger=False, period_ratio_threshold=None
    )
    aut_cusum.build(stream_cusum)
    assert any(t.cause == "frequency" for t in aut_cusum.transitions)


# ──────────────────────────────────────────────────────────────────────
# Tests — integration (real FTIO analysis)
# ──────────────────────────────────────────────────────────────────────


def test_phase_automaton_integration():
    """
    Integration test: synthetic bandwidth trace → FTIO analysis → automaton.

    Phase A: 6 bursts, period=5 s  (freq=0.20 Hz)
    Phase B: 6 bursts, period=15 s (freq=0.07 Hz)

    The automaton (CUSUM) should detect the frequency shift and produce at
    least 2 states with a clearly lower frequency in the final state.
    """
    phases = [
        (6, 5.0, 1.0, 1000.0),  # phase A: 6 bursts, period=5s, burst=1s
        (6, 15.0, 1.0, 1000.0),  # phase B: 6 bursts, period=15s, burst=1s
    ]
    time_arr, bw_arr, burst_ends = _generate_periodic_trace(phases, dt=1.0)
    predictions = _analyze_windows(time_arr, bw_arr, burst_ends, window=30.0, ranks=1)

    assert (
        len(predictions) >= 4
    ), f"Need at least 4 predictions to test the automaton, got {len(predictions)}"

    automaton = PhaseAutomaton(method="cusum")
    automaton.build(predictions)
    automaton.print_summary()

    assert (
        len(automaton.states) >= 2
    ), f"Expected at least 2 states, got {len(automaton.states)}"
    assert len(automaton.transitions) >= 1, "Expected at least one phase transition"

    freq_first = automaton.states[0].dominant_freq
    freq_last = automaton.states[-1].dominant_freq
    # Phase B has a period 3× longer → frequency should be significantly lower
    assert freq_last < freq_first * 0.8, (
        f"Final state freq ({freq_last:.4f} Hz) should be much lower than "
        f"initial state freq ({freq_first:.4f} Hz)"
    )


def test_phase_automaton_multi_rank():
    """
    Different rank configurations produce separate automata.

    ranks=1: longer I/O phases (period=15 s, freq≈0.07 Hz)
    ranks=4: shorter I/O phases (period=5 s, freq≈0.20 Hz)

    After building one automaton per rank config, we verify that each
    correctly reflects the different I/O period via the state's rank field.
    """
    phases_slow = [(8, 15.0, 1.0, 1000.0)]  # ranks=1: long period
    phases_fast = [(8, 5.0, 1.0, 1000.0)]  # ranks=4: short period

    time_slow, bw_slow, ends_slow = _generate_periodic_trace(phases_slow, dt=1.0)
    time_fast, bw_fast, ends_fast = _generate_periodic_trace(phases_fast, dt=1.0)

    preds_slow = _analyze_windows(time_slow, bw_slow, ends_slow, window=30.0, ranks=1)
    preds_fast = _analyze_windows(time_fast, bw_fast, ends_fast, window=30.0, ranks=4)

    aut_slow = PhaseAutomaton(method="cusum")
    aut_slow.build(preds_slow)

    aut_fast = PhaseAutomaton(method="cusum")
    aut_fast.build(preds_fast)

    aut_slow.print_summary()
    aut_fast.print_summary()

    # Ranks are tracked per-state (from the Prediction objects)
    if aut_slow.states:
        assert aut_slow.states[0].ranks == 1
    if aut_fast.states:
        assert aut_fast.states[0].ranks == 4

    if aut_slow.states and aut_fast.states:
        # The slow automaton should have a lower dominant frequency
        assert aut_slow.states[0].dominant_freq < aut_fast.states[0].dominant_freq, (
            f"ranks=1 freq ({aut_slow.states[0].dominant_freq:.4f} Hz) should be lower "
            f"than ranks=4 freq ({aut_fast.states[0].dominant_freq:.4f} Hz)"
        )


def test_phase_automaton_real_file():
    """
    Parse real JSONL files via main() and build an automaton.

    Each JSONL file yields one Prediction.  With multiple files we can
    exercise the automaton on real FTIO output rather than mocked data.
    Skipped automatically when no JSONL files are present.
    """
    files = sorted(glob.glob("examples/tmio/JSONL/*.jsonl"))
    if not files:
        pytest.skip("No JSONL files found in examples/tmio/JSONL/")

    from ftio.cli.ftio_core import main as ftio_main

    preds: list[Prediction] = []
    for f in files:
        try:
            p_list, _ = ftio_main(["ftio", f, "-e", "no"])
            preds.extend(p for p in p_list if not p.is_empty())
        except Exception:
            continue

    if len(preds) < 1:
        pytest.skip("No valid predictions extracted from real JSONL files")

    aut = PhaseAutomaton(method="cusum")
    aut.build(preds)
    aut.print_summary()

    assert len(aut.states) >= 1, "Automaton should have at least one state"
    # All states must carry a valid positive frequency
    for s in aut.states:
        assert s.dominant_freq > 0


# ──────────────────────────────────────────────────────────────────────
# Tests — edge cases
# ──────────────────────────────────────────────────────────────────────


def test_phase_automaton_invalid_method():
    with pytest.raises(ValueError, match="method must be"):
        PhaseAutomaton(method="unknown")


def test_phase_automaton_ksigma_cause_label():
    """Transitions from k-sigma carry cause='frequency'."""
    phase_a = [_mock_prediction(0.20, t * 5.0, (t + 1) * 5.0) for t in range(6)]
    phase_b = [
        _mock_prediction(0.05, 30.0 + t * 20.0, 30.0 + (t + 1) * 20.0) for t in range(4)
    ]

    aut = PhaseAutomaton(method="ksigma", rank_changes_trigger=False)
    aut.build(phase_a + phase_b)

    assert len(aut.transitions) >= 1
    assert all(t.cause == "frequency" for t in aut.transitions)


def test_phase_automaton_empty_predictions():
    """Automaton stays empty when all predictions are empty."""
    automaton = PhaseAutomaton(method="cusum")
    for _ in range(5):
        automaton.step(Prediction())  # empty prediction
    assert len(automaton.states) == 0
    assert len(automaton.transitions) == 0


if __name__ == "__main__":
    test_phase_automaton_mock_cusum()
    test_phase_automaton_mock_ph()
    test_phase_automaton_mock_adwin()
    test_phase_automaton_rank_change_trigger()
    test_phase_automaton_period_ratio()
    test_phase_automaton_cause_field()
    test_phase_automaton_integration()
    test_phase_automaton_multi_rank()
    test_phase_automaton_real_file()
    test_phase_automaton_invalid_method()
    test_phase_automaton_empty_predictions()
    print("\nAll tests passed.")
