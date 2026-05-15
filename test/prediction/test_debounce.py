"""
Tests for debounce / serial prediction mode in predictor_with_processes.

The ftio.prediction.processes module participates in a circular import chain
(processes → online_analysis → ftio.cli → predictor → pools → online_analysis).
All imports of that module are therefore deferred into the test functions, where
sys.modules is pre-populated with MagicMock stubs that break the cycle.

Author: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Version: 0.0.8

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers to break the circular import
# ---------------------------------------------------------------------------

_CYCLE_MODULES = [
    "ftio.prediction.online_analysis",
    "ftio.prediction.pools",
    "ftio.cli.predictor",
]


def _stub_cycle() -> dict[str, ModuleType]:
    """Insert MagicMock stubs for the modules that form the circular import
    cycle.  Returns the original entries so the caller can restore them."""
    saved = {}
    for name in _CYCLE_MODULES:
        saved[name] = sys.modules.pop(name, None)
        sys.modules[name] = MagicMock()
    # Make ftio.prediction.online_analysis.ftio_process look callable
    sys.modules["ftio.prediction.online_analysis"].ftio_process = MagicMock()
    return saved


def _restore_cycle(saved: dict) -> None:
    for name, mod in saved.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod
    # Force reload so real modules replace the stubs for later test
    for name in _CYCLE_MODULES:
        sys.modules.pop(name, None)


def _import_predictor():
    """Import (or reload) predictor_with_processes with the cycle broken."""
    # Remove any cached version of processes so it re-initialises against stubs
    sys.modules.pop("ftio.prediction.processes", None)
    import ftio.prediction.processes as proc_mod
    return proc_mod.predictor_with_processes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args(extra: list[str] | None = None) -> list[str]:
    """Build a minimal args list that parse_args can handle."""
    base = ["predictor", "dummy_file.json", "-e", "no"]
    if extra:
        base.extend(extra)
    return base


def _monitor_side_effect(n_triggers: int):
    """Side-effect for pm.monitor: init once, return new stamps for
    *n_triggers* calls, then raise KeyboardInterrupt."""
    calls = {"count": 0}

    def _side(name, stamp, procs=None):
        if stamp == "":
            return "stamp0", []
        calls["count"] += 1
        if calls["count"] > n_triggers:
            raise KeyboardInterrupt
        return f"stamp{calls['count']}", []

    return _side


# ---------------------------------------------------------------------------
# Tests: argparse flag (no circular-import risk — parse_args is clean)
# ---------------------------------------------------------------------------

class TestArgParsing:
    def test_debounce_default_false(self):
        from ftio.parse.args import parse_args
        parsed = parse_args(_make_args())
        assert parsed.debounce is False

    def test_debounce_flag_sets_true(self):
        from ftio.parse.args import parse_args
        parsed = parse_args(_make_args(["--debounce"]))
        assert parsed.debounce is True


# ---------------------------------------------------------------------------
# Tests: default (parallel) mode
# ---------------------------------------------------------------------------

class TestParallelMode:
    """predictor_with_processes without --debounce keeps the original behaviour."""

    def setup_method(self):
        self._saved = _stub_cycle()

    def teardown_method(self):
        _restore_cycle(self._saved)

    def test_spawns_new_proc_without_joining(self):
        """In parallel mode a new prediction is spawned per trigger, no join."""
        predictor_with_processes = _import_predictor()
        args = _make_args()  # no --debounce

        mock_proc = MagicMock()
        mock_proc.is_alive.return_value = False  # so join_procs reaps it

        with (
            patch(
                "ftio.prediction.processes.pm.monitor",
                side_effect=_monitor_side_effect(2),
            ),
            patch(
                "ftio.prediction.processes.handle_in_process",
                return_value=mock_proc,
            ) as mock_hip,
            patch("ftio.prediction.processes.print_data"),
            patch("ftio.prediction.processes.export_extrap"),
            patch("ftio.prediction.processes._export_phase_automaton"),
        ):
            sr = MagicMock()
            predictor_with_processes(sr, args)

        # Two file-change events → two prediction processes spawned
        assert mock_hip.call_count == 2
        # join() is never called inside the parallel loop
        mock_proc.join.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: debounce (serial) mode
# ---------------------------------------------------------------------------

class TestDebounceMode:
    """predictor_with_processes --debounce runs predictions serially."""

    def setup_method(self):
        self._saved = _stub_cycle()

    def teardown_method(self):
        _restore_cycle(self._saved)

    def test_joins_before_next_trigger(self):
        """In debounce mode proc.join() is called once per trigger."""
        predictor_with_processes = _import_predictor()
        args = _make_args(["--debounce"])
        mock_proc = MagicMock()

        with (
            patch(
                "ftio.prediction.processes.pm.monitor",
                side_effect=_monitor_side_effect(2),
            ),
            patch(
                "ftio.prediction.processes.handle_in_process",
                return_value=mock_proc,
            ) as mock_hip,
            patch("ftio.prediction.processes.print_data"),
            patch("ftio.prediction.processes.export_extrap"),
            patch("ftio.prediction.processes._export_phase_automaton"),
        ):
            sr = MagicMock()
            predictor_with_processes(sr, args)

        assert mock_hip.call_count == 2
        assert mock_proc.join.call_count == 2

    def test_stale_stamp_triggers_immediate_rerun(self):
        """After a prediction, if the stamp is stale, monitor returns immediately
        and another prediction is triggered — verifying the debounce re-trigger path."""
        predictor_with_processes = _import_predictor()
        args = _make_args(["--debounce"])
        stamps_seen: list[str] = []

        def _recording_monitor(name, stamp, procs=None):
            stamps_seen.append(stamp)
            if stamp == "":
                return "stamp0", []
            if stamp == "stamp0":
                return "stamp1", []
            raise KeyboardInterrupt

        with (
            patch("ftio.prediction.processes.pm.monitor", side_effect=_recording_monitor),
            patch("ftio.prediction.processes.handle_in_process", return_value=MagicMock()),
            patch("ftio.prediction.processes.print_data"),
            patch("ftio.prediction.processes.export_extrap"),
            patch("ftio.prediction.processes._export_phase_automaton"),
        ):
            predictor_with_processes(MagicMock(), args)

        # Stamp returned from first trigger must be passed into the next monitor call
        assert "stamp0" in stamps_seen
        assert "stamp1" in stamps_seen

    def test_no_concurrent_predictions(self):
        """In debounce mode at most one prediction process is alive at a time."""
        predictor_with_processes = _import_predictor()
        args = _make_args(["--debounce"])
        n_triggers = 4
        concurrent_counts: list[int] = []
        active: list = []

        def _make_proc(*a, **kw):
            proc = MagicMock()
            proc.join.side_effect = lambda: active.clear()
            active.append(proc)
            concurrent_counts.append(len(active))
            return proc

        with (
            patch(
                "ftio.prediction.processes.pm.monitor",
                side_effect=_monitor_side_effect(n_triggers),
            ),
            patch("ftio.prediction.processes.handle_in_process", side_effect=_make_proc),
            patch("ftio.prediction.processes.print_data"),
            patch("ftio.prediction.processes.export_extrap"),
            patch("ftio.prediction.processes._export_phase_automaton"),
        ):
            predictor_with_processes(MagicMock(), args)

        assert concurrent_counts, "no predictions were triggered"
        assert max(concurrent_counts) == 1, (
            f"concurrent predictions detected: {concurrent_counts}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
