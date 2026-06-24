# Frequency Methods

FTIO supports five frequency-analysis methods and two optional validation passes (autocorrelation and periodicity detection).  All methods operate on the same uniformly-resampled bandwidth signal `b_sampled` produced by the discretisation step.

- [Overview](#overview)
- [Choosing a method](#choosing-a-method)
- [DFT](#dft-discrete-fourier-transform)
- [STFT](#stft-short-time-fourier-transform)
- [ASTFT](#astft-adaptive-stft)
- [Discrete Wavelet Transform](#discrete-wavelet-transform-wave_disc)
- [Continuous Wavelet Transform](#continuous-wavelet-transform-wave_cont)
- [Autocorrelation](#autocorrelation)
- [Periodicity detection](#periodicity-detection)
- [EFD and VMD — Experimental](#efd-and-vmd--experimental)
- [Comparison table](#comparison-table)

---

## Overview

Select a method with the `-tr` / `--transformation` flag:

```bash
ftio trace.json -tr dft        # default
ftio trace.json -tr stft
ftio trace.json -tr astft
ftio trace.json -tr wave_disc
ftio trace.json -tr wave_cont
```

The sampling rate (`-f`) determines the Nyquist limit and therefore the highest detectable frequency.  A safe default is `-f 10` (10 Hz), which resolves periods as short as 0.2 s.  For very long traces with slow I/O cycles use a lower rate (e.g. `-f 1`).

---

## Choosing a method

| Situation | Recommended method |
|-----------|-------------------|
| Single stable periodic pattern, fast result needed | **DFT** (default) |
| Pattern frequency changes over time | **STFT** or **ASTFT** |
| Multiple simultaneous periodicities at different scales | **DWT** (`wave_disc`) |
| Short trace, want time-frequency map | **CWT** (`wave_cont`) |
| Offline analysis, highest accuracy needed | **ASTFT** (cm5 window sizing) |
| Validation / cross-check of DFT result | **Autocorrelation** (`-au`) |

---

## DFT — Discrete Fourier Transform

**Flag:** `-tr dft` (default)

The DFT transforms the full resampled signal into the frequency domain and identifies the dominant peak via the selected outlier-detection method (`-o`).

**Workflow:**

1. Discretise `bandwidth(t)` to `b_sampled` at rate `fs` (`-f`).
2. Apply DFT.
3. Compute power-spectral density (or amplitude if `-np`).
4. Detect outlier peaks with the chosen method (`-o`, default `z-score`).
5. Select the dominant frequency and compute confidence from the peak prominence.

**Key parameters:**

| Flag | Effect |
|------|--------|
| `-f FREQ` | Sampling rate; determines highest resolvable frequency (`fs/2`). |
| `-o METHOD` | Outlier detector: `z-score` (default), `dbscan`, `forest`, `lof`, `peak`. |
| `-t TOL` | Confidence threshold (default 0.8). |
| `-n N` | Extract up to N frequencies (default: dominant only). |
| `--fourier_fit` | Fit sinusoidal components for the N extracted frequencies. |
| `-d` | Dynamic time warping on the top-3 DFT frequencies. |
| `-ce` | Show cepstrum plot. |

**When to use:** The DFT is the fastest method and works well when the I/O period is stable across the entire trace.  For most HPC workloads this is the correct choice.

**Example:**
```bash
ftio trace.json                          # DFT, auto-detect dominant frequency
ftio trace.json -o dbscan -n 3           # extract up to 3 frequencies via DBSCAN
ftio trace.json -f 1 -t 0.6             # 1 Hz sampling, lower confidence threshold
```

---

## STFT — Short-Time Fourier Transform

**Flag:** `-tr stft`

The STFT applies the DFT on overlapping time windows, producing a time-frequency spectrogram.  This makes it possible to detect frequency changes that the global DFT would average out.

**Workflow:**

1. Discretise signal.
2. Divide into overlapping windows of length `W` (set with `--stft_window`).
3. Apply DFT to each window.
4. Average or select the dominant frequency across windows.

**Key parameters:**

| Flag | Default | Effect |
|------|---------|--------|
| `--stft_window` | `0` (auto) | Window length in samples or seconds (`20s`).  Auto sets W = 4 × detected period. |
| `-f FREQ` | `10` | Sampling rate. |
| `-o METHOD` | `z-score` | Outlier detector applied per window. |

**Window size trade-off:** A larger window gives better frequency resolution but worse time resolution.  The auto mode uses the DFT result to choose a sensible window (4× the detected period).

**When to use:** When the I/O period might drift or shift mid-trace.  More expensive than DFT but captures temporal variation.

**Example:**
```bash
ftio trace.json -tr stft
ftio trace.json -tr stft --stft_window 50s   # 50-second windows
```

---

## ASTFT — Adaptive STFT

**Flag:** `-tr astft`

The ASTFT is an offline-optimised variant of the STFT that automatically determines the best window size using the **cm5 concentration measure**.  It searches for the window length that maximises the energy concentration in the time-frequency plane — a principled, data-driven approach.

**Workflow:**

1. Discretise signal.
2. Scan candidate window sizes.
3. For each candidate, compute the cm5 energy-concentration measure.
4. Select the window that maximises concentration.
5. Run STFT with the optimal window.

**Key parameters:**

| Flag | Default | Effect |
|------|---------|--------|
| `--tfpf` | `0` | Time-frequency peak-filtering iterations (helps with noisy spectra). |
| `--stft_window` | `0` (auto) | Override the automatic cm5 window selection with a fixed value (samples or seconds, e.g. `20s`). When `0`, ASTFT determines the optimal window automatically. |

**When to use:** Best for offline analysis where the optimal window size is unknown.  Higher computational cost than plain STFT but produces the most accurate window.  Not recommended for online/streaming use due to the window-search overhead.

**Example:**
```bash
ftio trace.json -tr astft
ftio trace.json -tr astft --tfpf 2   # 2 peak-filtering passes
```

---

## Discrete Wavelet Transform — `wave_disc`

**Flag:** `-tr wave_disc`

The DWT decomposes the signal into multi-resolution approximation and detail coefficients across multiple frequency bands.  FTIO then applies a DFT on the approximation coefficients (the low-frequency component) to find the dominant I/O period.

**Workflow:**

1. Discretise signal.
2. Compute DWT at level `L` using the chosen wavelet family.
3. Determine dominant frequency from the approximation coefficients via DFT.

**Key parameters:**

| Flag | Default | Effect |
|------|---------|--------|
| `-le LEVEL` | `0` (auto) | Decomposition level.  Auto derives the level from the DFT result (≈ `1/(5·f_dom)`). |
| `--wavelet` | `db1` | Wavelet family (see `pywt.wavelist(kind="discrete")`). Common: `db1`, `db4`, `haar`, `sym4`. |
| `-f FREQ` | `10` | Sampling rate. |

**When to use:** When the signal has multiple simultaneous periodicities at different time scales, or when high-frequency noise should be separated from the low-frequency I/O cycle.  The DWT effectively acts as a filter bank before DFT analysis.

**Example:**
```bash
ftio trace.json -tr wave_disc
ftio trace.json -tr wave_disc -le 4 --wavelet db4
```

---

## Continuous Wavelet Transform — `wave_cont`

**Flag:** `-tr wave_cont`

The CWT produces a continuous time-frequency map (scalogram) by convolving the signal with scaled and translated copies of a mother wavelet.  FTIO extracts the dominant scale (frequency) from the scalogram ridge.

**Key parameters:**

| Flag | Default | Effect |
|------|---------|--------|
| `--wavelet` | `morl` | Mother wavelet.  Common: `morl` (Morlet), `mexh` (Mexican hat). |
| `-f FREQ` | `10` | Sampling rate. |

**When to use:** Short traces where time-frequency localisation matters, or for exploratory analysis when the period structure is unknown.  More expensive than DWT.

**Example:**
```bash
ftio trace.json -tr wave_cont
ftio trace.json -tr wave_cont --wavelet mexh
```

---

## Autocorrelation

**Flag:** `-au` / `--autocorrelation`

Autocorrelation is an **additional validation pass**, not a standalone method.  It runs alongside the selected frequency method (`-tr`) and independently estimates the dominant period by finding the lag at which the signal best correlates with itself.  The two results are then merged.

**When to use:** When you want extra confidence in the detected period.  Particularly useful for signals with a clear periodic structure but noisy spectrum.  Adds modest computation cost.

**Example:**
```bash
ftio trace.json -au                   # DFT + autocorrelation
ftio trace.json -tr stft -au          # STFT + autocorrelation
```

---

## Periodicity detection

**Flag:** `-p` / `--periodicity_detection`

After the dominant frequency is found, an optional periodicity score can be computed to characterise how strictly periodic the signal is.  Four methods are available:

| Value | Name | What it measures |
|-------|------|-----------------|
| `rpde` | Recurrence Period Density Entropy | Information-theoretic measure of periodicity |
| `sf` | Spectral flatness | How peaked vs. flat the spectrum is |
| `corr` | Correlation | Average correlation between consecutive periods |
| `ind` | Individual correlation | Per-period correlation against the template period |

The score is reported alongside the confidence value.  A high periodicity score (close to 1 for `corr` and `ind`) confirms that the detected frequency corresponds to a well-structured, repeating pattern.

**Example:**
```bash
ftio trace.json -p corr
ftio trace.json -p ind -au   # combine with autocorrelation
```

---

## EFD and VMD — Experimental

> **These methods are under active development.  Results may be unreliable and the interface may change.**

Two Adaptive Mode Decomposition methods are available as optional extras.  They require an additional dependency:

```bash
pip install "ftio[amd-libs]"
# or in editable mode:
pip install -e ".[amd-libs]"
```

### EFD — Empirical Fourier Decomposition

**Flag:** `-tr efd`

Decomposes the signal into intrinsic mode functions (IMFs) using Empirical Fourier Decomposition, then selects the periodic components via STFT-based analysis.  Each IMF is characterised by a centre frequency, amplitude, and phase.  The dominant frequency is the highest-energy periodic IMF.

```bash
ftio trace.json -tr efd
ftio trace.json -tr efd --tfpf 1   # with time-frequency peak filtering
```

**Current limitations:** Confidence values are hardcoded (0.85 for all components, 1.0 for the best).  The dominant frequency is returned via `get_dominant_freq()` as with other methods, but the confidence does not reflect actual detection quality.

### VMD — Variational Mode Decomposition

**Flag:** `-tr vmd`

Decomposes the signal into band-limited modes using VMD (Dragomiretskiy & Zosso, 2014), then selects periodic modes via STFT-based analysis.

```bash
ftio trace.json -tr vmd
ftio trace.json -tr vmd --tfpf 2
```

**Current limitations:** Amplitude values for VMD modes are not extracted (`amp = 0`), which means the amplitude-based dominant-frequency selection falls back to the first component.  Confidence is also hardcoded.  VMD works in practice but should be treated as experimental.

---

## Comparison table

| Method | Stability assumption | Time-frequency | Cost | Best for |
|--------|---------------------|----------------|------|----------|
| `dft` | Stationary signal | No | Low | Stable periodic I/O |
| `stft` | Slowly varying | Yes (windowed) | Medium | Drifting period |
| `astft` | Varying, optimal window | Yes | High | Offline, unknown window |
| `wave_disc` | Multi-scale | Approximate | Medium | Multi-scale patterns |
| `wave_cont` | Non-stationary | Yes | High | Short traces, exploration |
| `-au` (validation) | Any | No | Low | Cross-checking DFT |
| `efd` ⚠️ experimental | Any | No | Medium | Research / exploration |
| `vmd` ⚠️ experimental | Any | No | High | Research / exploration |
