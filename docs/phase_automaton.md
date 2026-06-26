# Phase Automaton

The phase automaton models I/O behaviour as a finite state machine where each **state** represents a stable frequency regime and **transitions** are fired when the regime changes.  It is designed for online prediction scenarios where the application's I/O pattern may shift — for example, between compute phases, I/O phases, or checkpointing bursts.

- [Concept](#concept)
- [Enabling the automaton](#enabling-the-automaton)
- [Transition triggers](#transition-triggers)
  - [Rank-count trigger](#rank-count-trigger)
  - [Period-ratio trigger](#period-ratio-trigger)
  - [Statistical detector](#statistical-detector)
- [Combining triggers](#combining-triggers)
- [Export](#export)
- [Examples](#examples)
- [Example output](#example-output)
- [Output JSON format](#output-json-format)

---

## Concept

Each time `predictor` produces a new prediction, the automaton checks whether the new prediction belongs to the current state or signals a phase transition:

```
prediction_n  ──►  automaton  ──► same state  (no action)
                      │
                      └──► transition  ──► new state  (window reset / output)
```

States accumulate a history of predictions.  When a transition fires, a new state is opened and the analysis window can be reset to focus on the new regime.

---

## Enabling the automaton

```bash
predictor live.jsonl -f 100 --phase-automaton
```

The automaton is only available in `predictor` (online mode), not in offline `ftio`.

---

## Transition triggers

Three independent triggers can fire a transition.  They can be used individually or combined (any one trigger firing is sufficient).

### Rank-count trigger

**Default: enabled.**  Fires immediately when the number of active I/O ranks in the new prediction differs from the current state's rank count.

Disable with `--pa-no-rank-trigger`:
```bash
predictor live.jsonl -f 100 --phase-automaton --pa-no-rank-trigger
```

### Period-ratio trigger

**Default: disabled.**  Fires when the ratio between the new and current dominant period exceeds a threshold:

```
max(T_new / T_cur,  T_cur / T_new)  >  RATIO
```

`RATIO = 1.5` means a 50 % change in period length triggers a transition.

```bash
predictor live.jsonl -f 100 --phase-automaton --pa-period-ratio 1.5
```

No warm-up period is needed; the check activates from the second prediction onwards.

### Statistical detector

**Default: `ksigma`.**  A statistical change-point test applied to the series of dominant-frequency values.  Choose with `--pa-method`:

| Method | Description | Characteristics |
|--------|-------------|-----------------|
| `ksigma` | State-adaptive k-sigma | Recommended.  Adapts threshold to within-state variance; robust to noise. |
| `cusum` | Adaptive-variance CUSUM | Fast reaction to sustained shifts; sensitive to variance changes. |
| `ph` | Page-Hinkley | Sequential test for monotonic drift; good for gradual changes. |
| `adwin` | Adaptive Windowing | Needs many samples or large frequency ratios to fire. |
| `none` | Disabled | Use only rank and/or period-ratio triggers. |

```bash
# Default: ksigma
predictor live.jsonl -f 100 --phase-automaton

# CUSUM
predictor live.jsonl -f 100 --phase-automaton --pa-method cusum

# No statistical detection, period-ratio only
predictor live.jsonl -f 100 --phase-automaton --pa-method none --pa-period-ratio 1.5
```

---

## Combining triggers

Any combination is valid.  A transition fires when **any** enabled trigger activates:

```bash
# All three triggers active
predictor live.jsonl -f 100 --phase-automaton \
    --pa-method ksigma \
    --pa-period-ratio 1.5
    # rank trigger is on by default

# Period-ratio and statistical only (no rank trigger)
predictor live.jsonl -f 100 --phase-automaton \
    --pa-method cusum \
    --pa-period-ratio 2.0 \
    --pa-no-rank-trigger
```

---

## Export

When `predictor` exits, the full automaton state (all states, transitions, and configuration) is written as JSON:

```bash
predictor live.jsonl -f 100 --phase-automaton --pa-export /tmp/my_automaton.json
```

Default path: `./phase_automaton.json`.

---

## Examples

```bash
# Minimal: default triggers (rank + ksigma)
predictor live.jsonl -f 100 --phase-automaton -e no

# Detect period changes of 50 % or more, disable statistical trigger
predictor live.jsonl -f 100 --phase-automaton \
    --pa-method none --pa-period-ratio 1.5 -e no

# Maximum sensitivity: all three triggers, Page-Hinkley for slow drifts
predictor live.jsonl -f 100 --phase-automaton \
    --pa-method ph --pa-period-ratio 1.3 -e no

# Export automaton, then inspect
predictor live.jsonl -f 100 --phase-automaton --pa-export run_automaton.json -e no
cat run_automaton.json
```

---

## Example output

The following examples use the demo script (`examples/API/phase_automaton_demo.py`) and can be reproduced via the `PhaseAutomaton` API directly.

### Three-phase signal — CUSUM detector

A synthetic trace with three distinct I/O periods fed one prediction at a time.  Each row shows the state count and whether a transition fired:

```
 Pred   freq (Hz)   period (s)  #states  #trans  event
─────  ──────────  ───────────  ───────  ──────  ────────────────────
    1       0.200         5.00        1       0
    2       0.200         5.00        1       0
    3       0.200         5.00        1       0
    4       0.200         5.00        1       0
    5       0.200         5.00        1       0
    6       0.050        20.00        2       1  → TRANSITION
    7       0.050        20.00        2       1
    8       0.050        20.00        2       1
    9       0.050        20.00        2       1
   10       0.050        20.00        2       1
   11       0.500         2.00        3       2  → TRANSITION
   12       0.500         2.00        3       2
   13       0.500         2.00        3       2
   14       0.500         2.00        3       2
   15       0.500         2.00        3       2
```

Calling `automaton.print_graph()` on the resulting automaton prints the state graph:

```
=================================================================
PhaseAutomaton graph  method='cusum'  states=3  transitions=2
─────────────────────────────────────────────────────────────────
  ┌──────────────────────────────┐
  │ S0                           │
  │ f = 0.2000 Hz                │
  │ T = 5.00 s                   │
  │ ranks = 1                    │
  │ dur   = 45.0 s               │
  └──────────────────────────────┘
                  │
                  ├─ freq shift (statistical)  @t=45.0 s
                  │  T: 5.00 s → 20.00 s
                  ▼
  ┌──────────────────────────────┐
  │ S1                           │
  │ f = 0.0500 Hz                │
  │ T = 20.00 s                  │
  │ ranks = 1                    │
  │ dur   = 82.0 s               │
  └──────────────────────────────┘
                  │
                  ├─ freq shift (statistical)  @t=127.0 s
                  │  T: 20.00 s → 2.00 s
                  ▼
  ┌──────────────────────────────┐
  │ S2                           │
  │ f = 0.5000 Hz                │
  │ T = 2.00 s                   │
  │ ranks = 1                    │
  │ dur   = 8.0 s                │
  └──────────────────────────────┘
=================================================================
```

### Rank-change trigger — same frequency, different rank counts

When the dominant period stays constant but the rank count shifts (e.g. checkpoint scaling), the rank trigger fires regardless of the statistical detector:

```
=================================================================
PhaseAutomaton graph  method=None  states=3  transitions=2
─────────────────────────────────────────────────────────────────
  ┌──────────────────────────────┐
  │ S0                           │
  │ f = 0.2000 Hz                │
  │ T = 5.00 s                   │
  │ ranks = 4                    │
  │ dur   = 30.0 s               │
  └──────────────────────────────┘
                  │
                  ├─ rank change  @t=30.0 s
                  │  T: 5.00 s → 5.00 s
                  ▼
  ┌──────────────────────────────┐
  │ S1                           │
  │ f = 0.2000 Hz                │
  │ T = 5.00 s                   │
  │ ranks = 8                    │
  │ dur   = 25.0 s               │
  └──────────────────────────────┘
                  │
                  ├─ rank change  @t=55.0 s
                  │  T: 5.00 s → 5.00 s
                  ▼
  ┌──────────────────────────────┐
  │ S2                           │
  │ f = 0.2000 Hz                │
  │ T = 5.00 s                   │
  │ ranks = 4                    │
  │ dur   = 20.0 s               │
  └──────────────────────────────┘
=================================================================
```

Three states are created even though the frequency never changes, because each rank count (4 → 8 → 4) defines a distinct operational regime.

---

## Output JSON format

The exported file contains:

```json
{
  "config": {
    "method": "ksigma",
    "period_ratio": null,
    "rank_trigger": true
  },
  "states": [
    {
      "id": 0,
      "predictions": [...],
      "dominant_freq_median": 0.092,
      "ranks": 384
    },
    {
      "id": 1,
      "predictions": [...],
      "dominant_freq_median": 0.045,
      "ranks": 192
    }
  ],
  "transitions": [
    {
      "from_state": 0,
      "to_state": 1,
      "trigger": "rank_change",
      "timestamp": 145.3
    }
  ]
}
```

`states` lists every identified regime; `transitions` records what caused each regime change and when.
