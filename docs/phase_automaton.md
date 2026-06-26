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
- [Reference Library](#reference-library)
  - [Application identity](#application-identity)
  - [First run — cold start](#first-run--cold-start)
  - [Subsequent runs — warm start](#subsequent-runs--warm-start)
  - [Malleable applications](#malleable-applications)
  - [Matching strategies](#matching-strategies)
  - [Library file format](#library-file-format)
  - [Combining with other flags](#combining-with-other-flags)

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

---

## Reference Library

The reference library extends the phase automaton with a second purpose: **predicting future transitions** by comparing a live run against compiled references from past runs of the same application.

Two kinds of prediction remain explicitly separate:

| | Source | Answers |
|---|---|---|
| **Frequency prediction** | DFT / wavelet (existing) | What is the dominant period *right now*? |
| **Transition prediction** | Reference library (new) | *When* will the period change, and to *what*? |

Enable with `--pa-library`:

```bash
predictor live.jsonl -f 100 --pa-library ./ftio_models --pa-app-name ior
```

`--pa-library` implies `--phase-automaton`; you do not need to pass both.

---

### Example output

The examples below show a 3-state IOR run (write → read → checkpoint) at 128 ranks.
The reference was built from 4 previous runs of the same application.

#### Run 1 — cold start

No reference exists yet.  FTIO builds the automaton from scratch and saves it on exit.

```
[ModelManager] Cold start — no reference for ior/ranks_128. Building automaton from this run.

[PREDICTOR] (#1): Started
[PREDICTOR] (#1): Dominant freq 0.518 Hz (1.93 sec)
[PREDICTOR] (#1): Freq candidates (1 found):
[PREDICTOR] (#1):    0) 0.52 Hz -- conf 0.87
[PREDICTOR] (#1): Time window 2.000 sec ([0.000,2.000] sec)
[PREDICTOR] (#1): Total bytes 512 MB
[PREDICTOR] (#1): Phase automaton: State 0 — freq=0.5181 Hz, period=1.93 s, ranks=128, n_preds=1
[PREDICTOR] (#1): Reference (greedy): cold start — no library match. Learning from this run.
[PREDICTOR] (#1): Ended
...
^C
[PhaseAutomaton] Saved to ./phase_automaton.json  (3 states, 2 transitions)
[AutomatonLibrary] Saved ior/ranks_128 → ./ftio_models/ior/ranks_128.json (1 run(s), 3 states)
```

---

#### Run 2+ — warm start

A reference is loaded.  Each prediction now shows a transition forecast alongside the frequency result.

**Startup:**
```
[ModelManager] Loaded ior/ranks_128 (3 states, 4 run(s))
```

**Early in state 1 — write phase (prediction #7, t=14s):**
```
[PREDICTOR] (#7): Started
[PREDICTOR] (#7): Dominant freq 0.518 Hz (1.93 sec)
[PREDICTOR] (#7): Freq candidates (1 found):
[PREDICTOR] (#7):    0) 0.52 Hz -- conf 0.87
[PREDICTOR] (#7): Time window 14.000 sec ([0.000,14.000] sec)
[PREDICTOR] (#7): Total bytes 3 GB
[PREDICTOR] (#7): Bytes transferred since last time 3 GB
[PREDICTOR] (#7): Phase automaton: State 0 — freq=0.5181 Hz, period=1.93 s, ranks=128, n_preds=7
[PREDICTOR] (#7): Reference (greedy): state 1/3, pos=0%, tracking=0.94
[PREDICTOR] (#7):   Transition in ~31.2s [28.1s–34.3s] → next period ≈ 0.96s
[PREDICTOR] (#7): Ended
```

**Approaching the first transition (prediction #22, t=44s):**
```
[PREDICTOR] (#22): Dominant freq 0.521 Hz (1.92 sec)
[PREDICTOR] (#22): Phase automaton: State 0 — freq=0.5181 Hz, period=1.93 s, ranks=128, n_preds=22
[PREDICTOR] (#22): Reference (greedy): state 1/3, pos=0%, tracking=0.96
[PREDICTOR] (#22):   Transition in ~1.2s [0.0s–3.3s] → next period ≈ 0.96s
[PREDICTOR] (#22): Ended
```

**Transition fires (prediction #24, t=48s):**
```
[PREDICTOR] (#24): Dominant freq 1.042 Hz (0.96 sec)
[PREDICTOR] (#24): Phase automaton: State 1 — freq=1.0417 Hz, period=0.96 s, ranks=128, n_preds=1
[PREDICTOR] (#24):   → TRANSITION: State 0 → 1  (0.5181 → 1.0417 Hz, cause='frequency')
[PREDICTOR] (#24): Reference (greedy): state 2/3, pos=50%, tracking=0.98
[PREDICTOR] (#24):   Transition in ~62.0s [56.8s–67.2s] → next period ≈ 1.93s
[PREDICTOR] (#24): Ended
```

**Mid read phase (prediction #40, t=80s):**
```
[PREDICTOR] (#40): Dominant freq 1.038 Hz (0.96 sec)
[PREDICTOR] (#40): Phase automaton: State 1 — freq=1.0417 Hz, period=0.96 s, ranks=128, n_preds=17
[PREDICTOR] (#40): Reference (greedy): state 2/3, pos=50%, tracking=0.97
[PREDICTOR] (#40):   Transition in ~30.0s [24.8s–35.2s] → next period ≈ 1.93s
[PREDICTOR] (#40): Ended
```

**Final state — checkpoint phase (prediction #72, t=145s):**
```
[PREDICTOR] (#72): Dominant freq 0.519 Hz (1.93 sec)
[PREDICTOR] (#72): Phase automaton: State 2 — freq=0.5181 Hz, period=1.93 s, ranks=128, n_preds=12
[PREDICTOR] (#72):   → TRANSITION: State 1 → 2  (1.0417 → 0.5181 Hz, cause='frequency')
[PREDICTOR] (#72): Reference (greedy): state 3/3, pos=100%, tracking=0.95
[PREDICTOR] (#72):   → APPLICATION IN FINAL REFERENCE STATE
[PREDICTOR] (#72): Ended
```

**Exit:**
```
[PhaseAutomaton] Saved to ./phase_automaton.json  (3 states, 2 transitions)
[AutomatonLibrary] Saved ior/ranks_128 → ./ftio_models/ior/ranks_128.json (5 run(s), 3 states)
```

---

#### Second run, first time (only 1 run in library, no timing bounds yet)

When a reference exists but was built from a single run, the next-period prediction is available but ETA bounds are not:

```
[PREDICTOR] (#7): Reference (greedy): state 1/3, pos=0%, tracking=0.93
[PREDICTOR] (#7):   Next period ≈ 0.96s (timing improves after ≥2 runs in library)
```

---

### Application identity

The library is organised as `<library_dir>/<app_name>/ranks_<key>.json`.  The `app_name` subdirectory separates different applications that happen to run at the same rank count.

```bash
--pa-app-name ior           # → ftio_models/ior/ranks_128.json
--pa-app-name hacc-io       # → ftio_models/hacc-io/ranks_9216.json
```

If `--pa-app-name` is omitted, the stem of the monitored filename is used
(e.g. `ior_write` from `ior_write.jsonl`).

---

### First run — cold start

On the first run for an app+config, no reference exists.  FTIO logs:

```
[ModelManager] Cold start — no reference for ior/ranks_128. Building automaton from this run.
```

The automaton is built normally.  On exit it is saved to the library as the first reference (std = 0 for all distributions — timing bounds require at least two runs).

---

### Subsequent runs — warm start

Once a reference exists, FTIO loads it and tracks position in it:

```
[ModelManager] Loaded ior/ranks_128 (3 states, 4 run(s))

[PREDICTOR] (#7): Reference (greedy): state 2/3, pos=50%, tracking=0.94
[PREDICTOR] (#7):   Transition in ~8.0s [5.5s–10.5s] → next period ≈ 0.96s
```

After the run completes, the new timing is merged into the library distributions using pooled statistics — estimates improve with each run.

When only one run is in the library (std = 0), the next-period prediction is still shown but no timing bounds are available:

```
[PREDICTOR] (#7):   Next period ≈ 0.96s (timing improves after ≥2 runs in library)
```

When the tracker reaches the last reference state:

```
[PREDICTOR] (#12):  → APPLICATION IN FINAL REFERENCE STATE
```

---

### Malleable applications

Rank changes mid-run are already captured by the automaton as state transitions (each state stores its `ranks`).  The library key encodes the full rank sequence, so a malleable run is stored separately from a fixed-rank run:

```bash
# fixed-rank run  → ftio_models/ior/ranks_128.json
# malleable run   → ftio_models/ior/ranks_16_32_128.json
```

The tracker uses rank count as a secondary matching signal alongside period, so a mid-run rank change in a live malleable run is a strong position cue against a malleable reference.

---

### Matching strategies

Three strategies are available via `--pa-match`.  All enforce forward-only progression through the reference states.

| Strategy | Description | Best for |
|---|---|---|
| `greedy` (default) | Nearest period + rank penalty at each step | Fast; large period changes between states |
| `dtw` | Align an observation window against reference suffixes using DTW | Noisy signals; short phases |
| `viterbi` | HMM forward pass with Gaussian emission on period | Best accuracy when ≥2 runs provide std estimates |

```bash
predictor live.jsonl -f 100 --pa-library ./ftio_models --pa-app-name ior --pa-match viterbi
```

---

### Library file format

Library files are compact JSON containing only per-state distribution statistics.  They are intentionally much smaller than the full `--pa-export` single-run snapshot.

```json
{
  "app_name": "ior",
  "rank_key": "128",
  "n_states": 3,
  "run_count": 4,
  "states": [
    {"period_mean": 1.93, "period_std": 0.08, "dwell_mean": 45.2, "dwell_std": 3.1, "ranks": 128, "n_samples": 4},
    {"period_mean": 0.96, "period_std": 0.04, "dwell_mean": 62.0, "dwell_std": 5.2, "ranks": 128, "n_samples": 4},
    {"period_mean": 1.93, "period_std": 0.07, "dwell_mean": 38.1, "dwell_std": 2.9, "ranks": 128, "n_samples": 4}
  ],
  "transition_causes": ["frequency", "frequency"]
}
```

---

### Combining with other flags

All existing `--pa-*` flags work alongside `--pa-library`:

```bash
predictor live.jsonl -f 100 \
    --pa-library ./ftio_models \
    --pa-app-name ior \
    --pa-method ksigma \
    --pa-period-ratio 1.5 \
    --pa-export ./this_run.json \
    --pa-match viterbi
```

`--pa-export` writes the single-run full snapshot as before; `--pa-library` additionally merges distributions into the library.
