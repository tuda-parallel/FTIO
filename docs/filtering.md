# Signal Filtering

FTIO can optionally apply a **Butterworth filter** to the resampled bandwidth signal before frequency analysis.  Pre-filtering is useful when the trace contains high-frequency noise, a strong low-frequency drift, or interfering components that would obscure the I/O period.

- [When to filter](#when-to-filter)
- [Filter types](#filter-types)
- [Flags](#flags)
- [Examples](#examples)
- [Time-frequency peak filtering (TFPF)](#time-frequency-peak-filtering-tfpf)

---

## When to filter

| Situation | Recommended filter |
|-----------|-------------------|
| High-frequency noise (sensor noise, OS jitter) obscures the I/O peak | **Lowpass** — remove everything above the I/O frequency |
| Slow drift / baseline wander in the bandwidth trace | **Highpass** — remove the DC trend |
| Only a known frequency band is of interest | **Bandpass** — isolate the target range |
| Multiple overlapping components at very different frequencies | **Bandpass** around the expected I/O period |

Filtering is applied *before* the selected frequency method.  It does not change the method choice (`-tr`); it conditions the input signal.

---

## Filter types

All three types use a zero-phase Butterworth IIR filter (`scipy.signal.butter` + `filtfilt`), which introduces no phase distortion.

### Lowpass

Passes frequencies **below** the cutoff and attenuates higher frequencies.

```bash
ftio trace.json --filter_type lowpass --filter_cutoff 0.5
```

### Highpass

Passes frequencies **above** the cutoff and attenuates lower frequencies (including DC).

```bash
ftio trace.json --filter_type highpass --filter_cutoff 0.01
```

### Bandpass

Passes a **band** between two cutoff frequencies.

```bash
ftio trace.json --filter_type bandpass --filter_cutoff 0.05 0.5
```

---

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--filter_type` | str | none | Filter type: `lowpass`, `highpass`, `bandpass`. Omit to disable filtering. |
| `--filter_cutoff` | float(s) | — | Cutoff frequency in Hz. Provide one value for lowpass/highpass; two values (`lo hi`) for bandpass. |
| `--filter_order` | int | `4` | Butterworth filter order. Higher order = sharper roll-off but more ringing risk. `4` is a safe default. |

---

## Examples

```bash
# Remove high-frequency noise above 1 Hz before DFT
ftio trace.json --filter_type lowpass --filter_cutoff 1.0

# Remove slow drift (below 0.01 Hz) before DFT
ftio trace.json --filter_type highpass --filter_cutoff 0.01

# Isolate the 0.05–0.5 Hz band (periods 2–20 s)
ftio trace.json --filter_type bandpass --filter_cutoff 0.05 0.5

# Sharper filter (order 8) around a known I/O period of ~10 s (0.1 Hz)
ftio trace.json --filter_type bandpass --filter_cutoff 0.05 0.2 --filter_order 8

# Combined with STFT for a drifting, noisy signal
ftio trace.json -tr stft --filter_type lowpass --filter_cutoff 2.0

# No plots, just console output
ftio trace.json --filter_type lowpass --filter_cutoff 0.5 -e no
```

---

## Time-frequency peak filtering (TFPF)

**Flag:** `--tfpf N`

TFPF is a different filtering technique specific to the **ASTFT** workflow.  It applies N iterations of time-frequency peak filtering to the spectrogram before extracting the dominant frequency.  TFPF suppresses spectrogram noise without blurring the time-frequency ridges.

```bash
ftio trace.json -tr astft --tfpf 2
```

`--tfpf 0` (default) disables TFPF.  Values of 1–3 are typical; higher values increase smoothing but also computation time.

> **Note:** `--tfpf` is only meaningful with `-tr astft`.  It has no effect with other methods.
