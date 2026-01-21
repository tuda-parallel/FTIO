"""
This module implements the Adaptive Short-Time Fourier Transform (ASTFT)
processing pipeline used in FTIO. It provides functionality for:

- Resampling bandwidth time-series to an evenly spaced time grid
- Applying optional denoising via TFPF-WVD filtering
- Performing ASTFT analysis in a three-step procedure
- Identifying and refining periodic components in the time-frequency domain
- Generating simple plots of the extracted components and time series

The module integrates with FTIO’s component selection and linking utilities
to identify meaningful frequency components and refine their properties
such as amplitude, frequency, and phase.

Author: josefinez
Editor: Ahmad Tarraf
Copyright (c) 2026 TU Darmstadt, Germany
Date: Oct 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from collections import namedtuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft
from scipy.signal import stft
from scipy.signal.windows import boxcar, gaussian

from ftio.freq.concentration_measures import cm3, cm4, cm5
from ftio.freq.denoise import tfpf_wvd
from ftio.freq.if_comp_separation import (  # binary_image,; binary_image_nprom,; binary_image_zscore_extended,
    binary_image_zscore,
    component_linking,
)

# from ftio.plot.plot_tf import plot_tf, plot_tf_contour


def astft(b_sampled, freq, bandwidth, time_b, args):
    t_start = time_b[0]
    t_end = time_b[-1]
    N = len(b_sampled)
    t = np.linspace(t_start, t_end, N, dtype=float)

    if args.tfpf:
        signal_hat = b_sampled
        for i in range(0, args.tfpf):
            signal_hat = tfpf_wvd(signal_hat, freq, t)
        astft_3step(b_sampled, freq, t, args, filtered=signal_hat)
    else:
        astft_3step(b_sampled, freq, t, args)


# mix & match
def astft_3step(signal, freq, time_b, args, filtered=None):
    if args.ptfr_window:
        win_len = args.ptfr_window
    elif filtered is None:
        win_len = cm5(signal, freq)
    else:
        win_len = cm5(filtered, freq)

    if filtered is None:
        signal_tfr, f, t = ptfr(signal, freq, win_len)
    else:
        signal_tfr, f, t = ptfr(filtered, freq, win_len)

    # image = binary_image_nprom(signal_tfr, n=3)
    image = binary_image_zscore(signal_tfr, freq, args)

    components = component_linking(image, freq, win_len)

    # simple astft
    simple_astft(components, signal, filtered, freq, time_b, args)


def ptfr(x, fs, win_len):
    win = boxcar(win_len)
    f, t, Zxx = stft(x, fs=fs, window=win, nperseg=win_len, noverlap=(win_len - 1))
    Zxx = Zxx.transpose()

    return Zxx, f, t


def test_signal(type="sinusoidal", noise=False):
    fs = 200
    duration = 10

    f_1 = 0.611
    f_2 = 3
    f_3 = 7

    t = np.linspace(0, duration, fs * duration)
    N = len(t)

    start_1 = int(0.03 * N)
    start_2 = int(0.6 * N)
    start_3 = int(0.85 * N)

    stop_1 = int(0.52 * N)
    stop_2 = int(0.8 * N)
    stop_3 = int(0.978 * N)

    amp_1 = 0.5
    amp_2 = 1
    amp_3 = 0.75

    s_1 = amp_1 * np.sin(2 * np.pi * f_1 * t[start_1:stop_1] + 2)
    s_2 = amp_2 * np.sin(2 * np.pi * f_2 * t[start_2:stop_2])
    s_3 = amp_3 * np.sin(2 * np.pi * f_3 * t[start_3:stop_3])

    signal = np.zeros(len(t))

    if type == "sinusoidal":
        signal[start_1:stop_1] = s_1
        signal[start_2:stop_2] = s_2
        signal[start_3:stop_3] = s_3
    elif type == "time bins":
        signal[start_1:stop_1] = np.where(s_1 >= amp_1 * 0.9, 0.5, 0)
        signal[start_2:stop_2] = np.where(s_2 >= amp_2 * 0.9, 1, 0)
        signal[start_3:stop_3] = np.where(s_3 >= amp_3 * 0.9, 0.75, 0)

    if noise:
        signal += np.random.normal(-0.1, 0.01, N)

    plt.plot(t, signal)
    plt.show()

    return signal, fs, t


def check_3_periods(signal, fs, exp_freq, est_period, start, end):
    win_len = (int)(3 * est_period)

    # area where component is expected
    bonus = est_period.astype(int)
    _start = start - bonus
    _end = end + bonus
    if _start < 0:
        _start = 0
    if _end > len(signal):
        _end = len(signal)

    subsignal = signal[_start:_end]

    win = boxcar(win_len)
    hop = 1
    f, t, Zxx = stft(
        subsignal, fs=fs, window=win, nperseg=win_len, noverlap=(win_len - hop)
    )

    exp_frq_bin = (exp_freq * win_len) / fs
    exp_frq_bin = np.round(exp_frq_bin).astype(int)

    comp = []
    flag = False
    start = 0
    # iterate over time instants
    for i in range(0, len(t)):
        yf = Zxx[: exp_frq_bin + 3, i].transpose()
        yf = np.abs(yf)
        # check if expected freq is peak
        if (
            exp_frq_bin > 1
            and np.abs(yf[exp_frq_bin]) > np.abs(yf[exp_frq_bin - 1])
            and np.abs(yf[exp_frq_bin]) > np.abs(yf[exp_frq_bin + 1])
        ):
            if not flag:
                start = i
                flag = True
            continue
        # or if expected + neighbor are peak
        # additional peak afterwards
        elif (
            len(yf) > exp_frq_bin + 2
            and np.abs(yf[exp_frq_bin]) > np.abs(yf[exp_frq_bin - 1])
            and np.abs(yf[exp_frq_bin]) > np.abs(yf[exp_frq_bin + 2])
            and np.abs(yf[exp_frq_bin + 1]) > np.abs(yf[exp_frq_bin - 1])
            and np.abs(yf[exp_frq_bin + 1]) > np.abs(yf[exp_frq_bin + 2])
        ):
            if not flag:
                start = i
                flag = True
            continue
        # additional peak before
        elif (
            np.abs(yf[exp_frq_bin]) > np.abs(yf[exp_frq_bin + 1])
            and np.abs(yf[exp_frq_bin]) > np.abs(yf[exp_frq_bin - 2])
            and np.abs(yf[exp_frq_bin - 1]) > np.abs(yf[exp_frq_bin + 1])
            and np.abs(yf[exp_frq_bin - 1]) > np.abs(yf[exp_frq_bin - 2])
        ):
            if not flag:
                start = i
                flag = True
            continue
        else:
            if not flag:
                continue
            stop = i
            c = start, stop
            comp.append(c)
            start = 0
            stop = 0
            flag = False
    if flag:
        stop = len(t) - 1
        c = start, stop
        comp.append(c)

    final_comp = []
    # check length component
    for c in comp:
        if (c[1] - c[0]) * hop >= win_len:
            c = c[0] + _start, c[1] + _start
            final_comp.append(c)

    return final_comp


def frq_refinement(signal, start, end, frq_est, fs, duration):
    est_period_time = 1 / frq_est
    est_period = len(signal) * (est_period_time / duration)

    end_per = start + 3 * est_period
    while end_per + est_period < end:
        end_per += est_period
    end_per = end_per.astype(int)

    # center window
    over = end - end_per
    start_per = start + over // 2
    end_per += over // 2

    yf = fft(signal[start_per:end_per])

    frqs = np.abs(yf[1 : len(yf) // 2])
    exp_frq_bin = (frq_est * (end_per - start_per)) / fs
    exp_frq_bin = exp_frq_bin.astype(int)

    ind = np.argmax(frqs[exp_frq_bin - 2 : exp_frq_bin + 2])
    ind = ind + (exp_frq_bin - 2) + 1

    frq_est_ref = ind * fs / len(yf)
    magn = np.abs(yf[ind])

    if (
        ind > 1
        and np.abs(yf[ind - 1]) > np.abs(yf[ind - 2])
        and np.abs(yf[ind - 1]) > np.abs(yf[ind + 1])
    ):
        frq_est_ref2 = (ind - 1) * fs / len(yf)
        frq_weighted = frq_est_ref * np.abs(yf[ind]) + frq_est_ref2 * np.abs(yf[ind - 1])
        frq_est_ref = frq_weighted / (np.abs(yf[ind]) + np.abs(yf[ind - 1]))
    elif np.abs(yf[ind + 1]) > np.abs(yf[ind + 2]) and np.abs(yf[ind + 1]) > np.abs(
        yf[ind - 1]
    ):
        frq_est_ref2 = (ind + 1) * fs / len(yf)
        frq_weighted = frq_est_ref * np.abs(yf[ind]) + frq_est_ref2 * np.abs(yf[ind + 1])
        frq_est_ref = frq_weighted / (np.abs(yf[ind]) + np.abs(yf[ind + 1]))

    if np.abs(1 - (frq_est / frq_est_ref)) < 0.005:
        return yf, ind, start_per, end_per

    frq_est = frq_est_ref
    # don't move too far away from PTFR frequency
    maxiter = 3
    for i in range(0, maxiter):
        yf_old = yf
        ind_old = ind
        start_per_old = start_per
        end_per_old = end_per
        magn_old = magn
        frq_est = frq_est_ref

        est_period_time = 1 / frq_est
        est_period = len(signal) * (est_period_time / duration)

        end_per = start + 3 * est_period
        while end_per + est_period < end:
            end_per += est_period
        end_per = end_per.astype(int)

        # center window
        over = end - end_per
        start_per = start + over // 2
        end_per += over // 2

        yf = fft(signal[start_per:end_per])

        frqs = np.abs(yf[1 : len(yf) // 2])
        exp_frq_bin = (frq_est * (end_per - start_per)) / fs
        exp_frq_bin = exp_frq_bin.astype(int)

        ind = np.argmax(frqs[exp_frq_bin - 2 : exp_frq_bin + 2])
        ind = ind + (exp_frq_bin - 2) + 1

        frq_est_ref = ind * fs / len(yf)
        magn = np.abs(yf[ind])

        if (
            ind > 1
            and np.abs(yf[ind - 1]) > np.abs(yf[ind - 2])
            and np.abs(yf[ind - 1]) > np.abs(yf[ind + 1])
        ):
            frq_est_ref2 = (ind - 1) * fs / len(yf)
            frq_weighted = frq_est_ref * np.abs(yf[ind]) + frq_est_ref2 * np.abs(
                yf[ind - 1]
            )
            frq_est_ref = frq_weighted / (np.abs(yf[ind]) + np.abs(yf[ind - 1]))
        elif np.abs(yf[ind + 1]) > np.abs(yf[ind + 2]) and np.abs(yf[ind + 1]) > np.abs(
            yf[ind - 1]
        ):
            frq_est_ref2 = (ind + 1) * fs / len(yf)
            frq_weighted = frq_est_ref * np.abs(yf[ind]) + frq_est_ref2 * np.abs(
                yf[ind + 1]
            )
            frq_est_ref = frq_weighted / (np.abs(yf[ind]) + np.abs(yf[ind + 1]))

        if magn < magn_old:
            return yf_old, ind_old, start_per_old, end_per_old

    return yf, ind, start_per, end_per


from scipy.signal import find_peaks


def simple_astft(components, signal, filtered, fs, time_b, args, merge=True, imfs=None):

    signal_plot = signal

    t_start = time_b[0]
    t_end = time_b[-1]

    N = len(signal)
    t = np.arange(t_start, t_end, (t_end - t_start) / N, dtype=float)

    duration = t_end - t_start

    if filtered is not None:
        # ax.plot(t, filtered)
        signal = filtered

    if merge:
        # merge interrupted components
        i = 0
        length = len(components)
        while i < length - 1:
            if components[i][1] == components[i + 1][1]:
                est_period_time = 1 / components[i][1]  # / fs
                est_period = len(signal) * (est_period_time / duration)

                # end - start
                dist = components[i + 1][0][0] - components[i][0][1]
                if dist < est_period:
                    time = components[i][0][0], components[i + 1][0][1]
                    components[i] = time, components[i][1], components[2]
                    del components[i + 1]
                    length -= 1
            i += 1

    Component = namedtuple("Component", ["start", "end", "amp", "freq", "phase"])
    per_comp = []

    for i in components:
        start = i[0][0]
        end = i[0][1] + 1
        window = signal[start:end]
        comp_length = i[0][1] - i[0][0]

        est_period_time = 1 / i[1]
        est_period = len(signal) * (est_period_time / duration)

        # skip too short components
        skip_threshold = 0.9
        min_length = 3 * est_period * skip_threshold
        if comp_length < min_length:
            continue

        # two strategies
        # window 3 periods: everywhere where argmax matches, cant refine frequency
        # window londest possible multiple of periods smaller comp: choose based on magnitude

        # use window with length multiple of bin im period to verify
        # 3 periods: better time resolution
        # worse frq -> advantage, small changes cannot be represented, more robust
        # get final frq afterwards
        final_components = check_3_periods(signal, fs, i[1], est_period, start, end)

        for fc in final_components:
            # retrieve final frq est & functional from longest possible multiple
            if imfs is None:
                yf, peak, start_frq, stop_frq = frq_refinement(
                    signal, fc[0], fc[1], i[1], fs, duration
                )
            else:
                yf, peak, start_frq, stop_frq = frq_refinement(
                    imfs[i[3]], fc[0], fc[1], i[1], fs, duration
                )

            amp_final = np.abs(yf[peak]) / (stop_frq - start_frq)
            frq_final = peak * fs / (stop_frq - start_frq)

            # compute phase shift
            # phi = -2 * pi * f * t_shift
            phi_shift = -2 * np.pi * frq_final * (t[start_frq - fc[0]])
            phase_final = np.angle(yf[peak] * np.exp(1j * phi_shift))

            # merge components with same frequency and phase
            merged = False
            for c in per_comp:
                if c.freq == frq_final and c.end > fc[0]:
                    # phase
                    phi_shift_comp = -2 * np.pi * frq_final * (t[start_frq - c.start])
                    phase_comp = np.angle(yf[peak] * np.exp(1j * phi_shift_comp))

                    # TODO: modulo pi?, threshold?
                    if np.abs(c.phase - phase_comp) < 0.001:
                        c.end = fc[1]
                        merged = True
                        break

            if not merged:
                comp_ext = Component(fc[0], fc[1], amp_final, frq_final, phase_final)
                per_comp.append(comp_ext)

    if per_comp:
        # plt.plot(t, signal_plot)
        min_len = min(len(t), len(signal_plot))
        plt.plot(t[:min_len], signal_plot[:min_len])

        for p in per_comp:
            estimate = p.amp * np.cos(2 * np.pi * p.freq * t + p.phase)
            # plt.plot(t[p.start : p.end], estimate[0 : p.end - p.start], label=p.freq)
            t_seg = t[p.start : p.end]
            est_seg = estimate[: len(t_seg)]  # ensures same length
            plt.plot(t_seg, est_seg, label=p.freq)

        plt.legend()
        plt.show()

    return per_comp
