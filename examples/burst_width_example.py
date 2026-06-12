"""
Example: energy-concentration burst-width estimation on a synthetic I/O trace.

Three subplots:
  1. Raw bandwidth signal with period boundaries and detected burst width
  2. Per-period burst widths (median ± IQR band)
  3. Energy concentration curve for one example period
"""

import matplotlib.pyplot as plt
import numpy as np

# ── Synthetic signal ────────────────────────────────────────────────────────
rng = np.random.default_rng(42)

fs = 100  # samples/s
T = 5.0  # period (s)
f_dom = 1.0 / T
n_periods = 8
duration = n_periods * T

t = np.arange(0, duration, 1 / fs)
signal = np.zeros(len(t))

burst_centers = np.arange(T / 2, duration, T)

shapes = [
    "single",
    "double",
    "wide",
    "ramp",
    "single",
    "double_trail",
    "narrow",
    "single",
]

for i, tc in enumerate(burst_centers):
    shape = shapes[i % len(shapes)]

    if shape == "single":
        # Clean single burst, moderate width
        w = 1.0 + rng.uniform(-0.1, 0.2)
        signal += (0.9 + rng.uniform(-0.1, 0.2)) * np.exp(
            -0.5 * ((t - tc) / (w / 3)) ** 2
        )

    elif shape == "double":
        # Two comparable peaks close together
        signal += 0.85 * np.exp(-0.5 * ((t - (tc - 0.5)) / 0.22) ** 2)
        signal += 0.75 * np.exp(-0.5 * ((t - (tc + 0.5)) / 0.22) ** 2)

    elif shape == "wide":
        # One wide flat-top burst (trapezoid via sum of gaussians)
        for off in np.linspace(-0.7, 0.7, 6):
            signal += 0.18 * np.exp(-0.5 * ((t - (tc + off)) / 0.18) ** 2)

    elif shape == "ramp":
        # Asymmetric: fast ramp-up, slow decay
        mask = (t >= tc - 1.2) & (t <= tc + 1.2)
        ramp = np.zeros(len(t))
        ramp[mask] = np.where(
            t[mask] < tc, (t[mask] - (tc - 1.2)) / 1.2, np.exp(-2.5 * (t[mask] - tc))
        )
        signal += ramp

    elif shape == "double_trail":
        # Main burst + significant trailing flush after a gap
        signal += 0.95 * np.exp(-0.5 * ((t - tc) / 0.25) ** 2)
        signal += 0.55 * np.exp(-0.5 * ((t - (tc + 1.3)) / 0.20) ** 2)

    elif shape == "narrow":
        # Very narrow spike
        signal += 1.1 * np.exp(-0.5 * ((t - tc) / 0.12) ** 2)

# Background noise + small constant baseline
signal += rng.normal(0, 0.02, len(t))
signal += 0.04  # non-zero idle baseline
signal = np.clip(signal, 0, None)

# ── Energy-concentration estimator ─────────────────────────────────────────
T_samples = int(T * fs)
energy_fraction = 0.95


def min_contiguous_window(power, fraction):
    """Shortest contiguous interval containing `fraction` of total energy."""
    target = fraction * np.sum(power)
    left = 0
    window_sum = 0.0
    min_width = len(power)
    min_left = 0
    for right in range(len(power)):
        window_sum += power[right]
        while window_sum >= target:
            w = right - left + 1
            if w < min_width:
                min_width = w
                min_left = left
            window_sum -= power[left]
            left += 1
    return min_width, min_left


burst_widths = []
period_slices = []

for k in range(n_periods):
    start = k * T_samples
    end = start + T_samples
    segment = signal[start:end]

    power = segment**2
    n_active, win_left = min_contiguous_window(power, energy_fraction)
    burst_widths.append(n_active / fs)
    period_slices.append((start, end, win_left, win_left + n_active))

burst_widths = np.array(burst_widths)
median_bw = np.median(burst_widths)
min_bw = np.min(burst_widths)
max_bw = np.max(burst_widths)

# Example period for panel 3 — use period 1 (double-peak, most illustrative)
ex_k = 1
ex_start, ex_end, ex_wl, ex_wr = period_slices[ex_k]
ex_segment = signal[ex_start:ex_end]
ex_power = ex_segment**2
ex_cum_contiguous = np.cumsum(ex_power) / np.sum(ex_power)  # left-to-right cumsum

# ── Plot ────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(11, 9))
fig.suptitle(
    "Energy-concentration burst-width estimation", fontsize=13, fontweight="bold"
)

# ── Panel 1: signal + period boundaries + burst width annotation ──────────
ax = axes[0]
ax.plot(t, signal, color="#2c7bb6", lw=1.2, label="Bandwidth")
ax.set_ylabel("Bandwidth (a.u.)")
ax.set_xlabel("Time (s)")

for k in range(n_periods + 1):
    ax.axvline(k * T, color="gray", lw=0.8, ls="--", alpha=0.5)

for k, (start, end, win_left, win_right) in enumerate(period_slices):
    shade_start = t[start + win_left]
    shade_end = t[min(start + win_right, end) - 1]
    ax.axvspan(
        shade_start,
        shade_end,
        alpha=0.18,
        color="#d7191c",
        label=f"Estimated burst ({int(energy_fraction*100)}% energy)" if k == 0 else "",
    )

# Annotate one period
k_ann = 3
start_ann, end_ann, wl_ann, wr_ann = period_slices[k_ann]
t_shade_start = t[start_ann + wl_ann]
t_shade_end = t[min(start_ann + wr_ann, end_ann) - 1]
bw_ann = burst_widths[k_ann]
mid_ann = (t_shade_start + t_shade_end) / 2
ax.annotate(
    "",
    xy=(t_shade_end, 0.80),
    xytext=(t_shade_start, 0.80),
    arrowprops={"arrowstyle": "<->", "color": "#d7191c", "lw": 1.5},
)
ax.text(mid_ann, 0.86, f"τ = {bw_ann:.2f}s", ha="center", color="#d7191c", fontsize=9)

ax.legend(loc="upper right", fontsize=8)
ax.set_xlim(0, duration)
ax.set_ylim(-0.05, 1.45)
ax.set_title(
    "Irregular bandwidth signal — sub-bursts, variable amplitude, noise", fontsize=10
)

# ── Panel 2: per-period burst widths ─────────────────────────────────────
ax = axes[1]
periods_x = np.arange(1, n_periods + 1)
ax.bar(
    periods_x, burst_widths, color="#2c7bb6", alpha=0.7, width=0.55, label="Per-period τ"
)
ax.axhline(median_bw, color="#d7191c", lw=1.8, ls="-", label=f"Median = {median_bw:.2f}s")
ax.axhline(min_bw, color="darkorange", lw=1.2, ls="--", label=f"Min = {min_bw:.2f}s")
ax.axhline(max_bw, color="green", lw=1.2, ls="--", label=f"Max = {max_bw:.2f}s")
ax.fill_between([0.5, n_periods + 0.5], min_bw, max_bw, color="#d7191c", alpha=0.07)
ax.set_xlabel("Period index")
ax.set_ylabel("Burst width (s)")
ax.set_xticks(periods_x)
ax.set_xlim(0.3, n_periods + 0.7)
ax.set_ylim(0, T * 0.65)
ax.legend(fontsize=8)
duty_cycle = median_bw * f_dom
ax.set_title(
    f"Per-period burst width  —  median={median_bw:.2f}s, min={min_bw:.2f}s, max={max_bw:.2f}s  |  duty cycle={duty_cycle:.2f}",
    fontsize=10,
)

# ── Panel 3: contiguous cumulative energy for the double-peak period ─────
ax = axes[2]
t_ex = t[ex_start:ex_end] - t[ex_start]  # time relative to period start

ax.fill_between(
    t_ex,
    ex_power / np.max(ex_power),
    color="#2c7bb6",
    alpha=0.35,
    label="Instantaneous power (normalised)",
)
ax.plot(
    t_ex,
    ex_cum_contiguous,
    color="#2c7bb6",
    lw=1.8,
    label="Cumulative energy (left→right)",
)

# Mark 95% level
idx_95 = np.searchsorted(ex_cum_contiguous, energy_fraction)
ax.axhline(
    energy_fraction,
    color="#d7191c",
    lw=1.2,
    ls="--",
    label=f"{int(energy_fraction*100)}% energy level",
)

# Shade the contiguous window
t_win_start = t_ex[ex_wl]
t_win_end = t_ex[min(ex_wr, len(t_ex)) - 1]
ax.axvspan(
    t_win_start,
    t_win_end,
    alpha=0.18,
    color="#d7191c",
    label=f"Contiguous window: τ = {burst_widths[ex_k]:.2f}s",
)

# Compare: sorted approach (old method)
ex_sorted_idx = np.argsort(ex_power)[::-1]
ex_sorted_cum = np.cumsum(ex_power[ex_sorted_idx]) / np.sum(ex_power)
n_sorted = np.searchsorted(ex_sorted_cum, energy_fraction) + 1
ax.axvline(
    n_sorted / fs,
    color="darkorange",
    lw=1.2,
    ls=":",
    label=f"Sorted-samples approach: τ = {n_sorted/fs:.2f}s  (too short)",
)

ax.set_xlabel("Time within period (s)")
ax.set_ylabel("Energy (normalised)")
ax.set_xlim(0, T)
ax.set_ylim(0, 1.15)
ax.legend(fontsize=8)
ax.set_title(
    f"Period {ex_k + 1} (double-peak): contiguous window vs. sorted-samples", fontsize=10
)

plt.tight_layout()
plt.savefig(
    "/d/github/FTIO/examples/burst_width_example.png", dpi=150, bbox_inches="tight"
)
plt.show()
print("Saved: examples/burst_width_example.png")
