"""
ReferenceAutomaton: compiled reference built from one or more profiling runs.

Unlike PhaseAutomaton (which records a single live run), ReferenceAutomaton
stores per-state distribution statistics and merges new runs using pooled
variance — the topology (number of states, rank sequence) is the stable part;
timing distributions improve with each additional run.

Author: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Licensed under the BSD 3-Clause License.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class StateStats:
    """Distribution statistics for a single reference state, aggregated across runs."""

    period_mean: float
    period_std: float
    dwell_mean: float  # seconds spent in this state
    dwell_std: float
    ranks: int = 0
    n_samples: int = 1


class ReferenceAutomaton:
    """
    Compiled reference automaton built from one or more PhaseAutomaton exports.

    Each state holds distribution statistics (mean ± std) rather than raw
    observations.  Multiple runs are merged using pooled statistics; the
    topology (n_states, rank sequence) must match for a merge to succeed.

    Library key: derived from the rank sequence across states, e.g. "128" for
    a fixed-rank run, "16_32_128" for a malleable run that scaled up twice.
    """

    def __init__(
        self,
        app_name: str,
        rank_key: str,
        n_states: int,
        state_stats: list[StateStats],
        transition_causes: list[str],
        run_count: int = 1,
    ):
        self.app_name = app_name
        self.rank_key = rank_key
        self.n_states = n_states
        self.state_stats = state_stats
        self.transition_causes = transition_causes
        self.run_count = run_count

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def period_sequence(self) -> list[float]:
        return [s.period_mean for s in self.state_stats]

    @property
    def rank_sequence(self) -> list[int]:
        return [s.ranks for s in self.state_stats]

    # ------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------

    @staticmethod
    def rank_key_from_sequence(ranks: list[int]) -> str:
        """Derive a library key from a sequence of observed rank counts.

        Consecutive duplicates are collapsed so the key reflects distinct
        rank configurations: [16, 16, 32, 32, 128] → "16_32_128".
        """
        if not ranks:
            return "0"
        unique: list[int] = []
        for r in ranks:
            if not unique or r != unique[-1]:
                unique.append(r)
        return "_".join(str(r) for r in unique)

    @classmethod
    def from_automaton_dict(
        cls,
        data: dict,
        app_name: str,
        rank_key: str,
    ) -> ReferenceAutomaton:
        """Build from a single PhaseAutomaton.to_dict() export (one run, std = 0)."""
        raw_states = data.get("states", [])
        raw_transitions = data.get("transitions", [])

        stats: list[StateStats] = []
        for s in raw_states:
            period = s.get("period")
            if period is None and s.get("dominant_freq"):
                period = 1.0 / s["dominant_freq"]
            dur = s.get("duration")
            stats.append(
                StateStats(
                    period_mean=float(period) if period is not None else np.nan,
                    period_std=0.0,
                    dwell_mean=float(dur) if dur is not None else np.nan,
                    dwell_std=0.0,
                    ranks=int(s.get("ranks", 0)),
                    n_samples=1,
                )
            )

        causes = [t.get("cause", "frequency") for t in raw_transitions]

        return cls(
            app_name=app_name,
            rank_key=rank_key,
            n_states=len(raw_states),
            state_stats=stats,
            transition_causes=causes,
            run_count=1,
        )

    @classmethod
    def from_dict(cls, data: dict) -> ReferenceAutomaton:
        """Load from a previously saved reference JSON (our own compact format)."""
        raw = data.get("states", [])
        stats: list[StateStats] = []
        for s in raw:
            pm = s.get("period_mean")
            ps = s.get("period_std") or 0.0
            dm = s.get("dwell_mean")
            ds = s.get("dwell_std") or 0.0
            stats.append(
                StateStats(
                    period_mean=float(pm) if pm is not None else np.nan,
                    period_std=float(ps),
                    dwell_mean=float(dm) if dm is not None else np.nan,
                    dwell_std=float(ds),
                    ranks=int(s.get("ranks", 0)),
                    n_samples=int(s.get("n_samples", 1)),
                )
            )
        return cls(
            app_name=data.get("app_name", "unknown"),
            rank_key=data.get("rank_key", "0"),
            n_states=data["n_states"],
            state_stats=stats,
            transition_causes=data.get("transition_causes", []),
            run_count=data.get("run_count", 1),
        )

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    def merge(self, other: ReferenceAutomaton) -> ReferenceAutomaton:
        """Merge another run into this reference using pooled statistics.

        Only succeeds when both automata have the same number of states.
        If topologies differ (the application changed phase structure),
        returns self unchanged — the caller should save the new run under a
        different key rather than corrupting the existing reference.
        """
        if other.n_states != self.n_states:
            return self

        merged: list[StateStats] = []
        for a, b in zip(self.state_stats, other.state_stats, strict=True):
            pm, ps = _pool(
                a.period_mean,
                a.period_std,
                a.n_samples,
                b.period_mean,
                b.period_std,
                b.n_samples,
            )
            dm, ds = _pool(
                a.dwell_mean,
                a.dwell_std,
                a.n_samples,
                b.dwell_mean,
                b.dwell_std,
                b.n_samples,
            )
            merged.append(
                StateStats(
                    period_mean=pm,
                    period_std=ps,
                    dwell_mean=dm,
                    dwell_std=ds,
                    ranks=a.ranks,
                    n_samples=a.n_samples + b.n_samples,
                )
            )

        return ReferenceAutomaton(
            app_name=self.app_name,
            rank_key=self.rank_key,
            n_states=self.n_states,
            state_stats=merged,
            transition_causes=self.transition_causes,
            run_count=self.run_count + other.run_count,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        def _f(v: float) -> float | None:
            if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                return None
            return float(v)

        return {
            "app_name": self.app_name,
            "rank_key": self.rank_key,
            "n_states": self.n_states,
            "run_count": self.run_count,
            "states": [
                {
                    "period_mean": _f(s.period_mean),
                    "period_std": _f(s.period_std),
                    "dwell_mean": _f(s.dwell_mean),
                    "dwell_std": _f(s.dwell_std),
                    "ranks": s.ranks,
                    "n_samples": s.n_samples,
                }
                for s in self.state_stats
            ],
            "transition_causes": self.transition_causes,
        }


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _pool(
    m1: float,
    s1: float,
    n1: int,
    m2: float,
    s2: float,
    n2: int,
) -> tuple[float, float]:
    """Merge two (mean, std, n) triplets into a pooled (mean, std)."""
    if np.isnan(m1):
        return m2, s2
    if np.isnan(m2):
        return m1, s1
    n = n1 + n2
    m = (n1 * m1 + n2 * m2) / n
    var = (n1 * (s1**2 + (m1 - m) ** 2) + n2 * (s2**2 + (m2 - m) ** 2)) / n
    return m, float(np.sqrt(var))
