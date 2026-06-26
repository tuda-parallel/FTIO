"""
ftio.modeling — reference automaton library and transition prediction.

PhaseAutomaton (moved here from ftio.prediction) models a single live run as
a finite state machine.  The rest of this package adds a reference layer on
top: compiled multi-run references, position tracking, and transition forecasts.

Public API
----------
PhaseAutomaton, PhaseState, Transition
    Live I/O phase state machine (original home: ftio.prediction.phase_automaton,
    kept there as a backward-compatibility shim).

ReferenceAutomaton, StateStats
    Compiled reference from one or more profiling runs; stores per-state
    distributions (mean ± std) rather than raw observations.

AutomatonLibrary
    Directory-based store: <library>/<app_name>/ranks_<key>.json

StateTracker, MatchStrategy
    Tracks position in a reference automaton from live observations.
    Strategies: greedy, dtw, viterbi.

TransitionPredictor, TransitionForecast
    Predicts time-to-next-transition and next-state period from the reference.

ModelManager
    Top-level entry point — wires all components for the online pipeline.
"""

from ftio.modeling.automaton_library import AutomatonLibrary
from ftio.modeling.model_manager import ModelManager
from ftio.modeling.phase_automaton import PhaseAutomaton, PhaseState, Transition
from ftio.modeling.reference_automaton import ReferenceAutomaton, StateStats
from ftio.modeling.state_tracker import MatchStrategy, StateTracker
from ftio.modeling.transition_predictor import TransitionForecast, TransitionPredictor

__all__ = [
    "PhaseAutomaton",
    "PhaseState",
    "Transition",
    "ReferenceAutomaton",
    "StateStats",
    "AutomatonLibrary",
    "StateTracker",
    "MatchStrategy",
    "TransitionPredictor",
    "TransitionForecast",
    "ModelManager",
]
