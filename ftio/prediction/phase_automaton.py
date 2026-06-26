# Backward-compatibility shim — module moved to ftio.modeling.phase_automaton.
from ftio.modeling.phase_automaton import PhaseAutomaton, PhaseState, Transition

__all__ = ["PhaseAutomaton", "PhaseState", "Transition"]
