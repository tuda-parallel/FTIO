"""
TODO:
OASTFT
- use correct fs in stft
- upgrade to ShortTimeFFT
"""

import math
import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft, ifft
from scipy.signal import stft
from scipy.signal.windows import gaussian
from ftio.freq.if_comp_separation import (
            binary_image,
            binary_image_nprom,
            binary_image_zscore,
            binary_image_zscore_extended,
            component_linking)
from ftio.freq.anomaly_detection import z_score
from ftio.freq.concentration_measures import cm3, cm4, cm5
from ftio.freq.denoise import tfpf_wvd
from ftio.plot.plot_tf import plot_tf, plot_tf_contour

def astft(b_sampled, freq, b_oversampled, freq_over, bandwidth, time_b, args):
    test, fs, time = test_signal("sinusoidal", noise=False)
    astft_mnm(test, fs, time, args)
    plot_tf(test, fs, time, win_len=350, step=0.1)

    #tf_samp = tfpf_wvd(test, fs, time)
    #plot_tf(tf_samp, fs, time)
    #decomp_vmd(tf_samp, time_b)

# mix & match
def astft_mnm(signal, freq, time_b, args, filtered=None):
    if filtered is None:
        win_len = cm3(signal)
    else:
        win_len = cm3(filtered)

    # sigma
    sigma = int(win_len / 2.35482)

    if filtered is None:
        signal_tfr, f, t = ptfr(signal, freq, win_len, sigma)
    else:
        signal_tfr, f, t = ptfr(filtered, freq, win_len, sigma)

    image = binary_image_nprom(signal_tfr, n=3)
    #image = binary_image_zscore(signal_tfr, freq, args)

    components = component_linking(image)

    # simple astft
    simple_astft(components, signal, filtered, freq, time_b, args)

"""
Pei, S. C., & Huang, S. G. (2012).
STFT with adaptive window width based on the chirp rate.
IEEE Transactions on Signal Processing, 60(8), 4065-4080.
"""
def astft_tf(x):
    win_len = cm3(signal)

"""
Abdoush, Y., Pojani, G., & Corazza, G. E. (2019).
Adaptive instantaneous frequency estimation of multicomponent signals
based on linear time–frequency transforms.
IEEE Transactions on Signal Processing, 67(12), 3100-3112
"""
def oastft(x):
    # regular rate, ratio effective bandwidth and effective time duration
    v_0 = regular_rate(x)

    # (3/7)^(1/4) * 1/sqrt(2*pi*v_0)
    sigma = 0.8091067 / (math.sqrt(2 * math.pi * v_0))

    # FWHM: 2*sqrt(2*ln(2))*sigma = 2.35482*sigma
    win_len = int(2.35482 * sigma)

    # 1: construct a ptfr
    x_ptfr = ptfr(x, win_len, sigma)

    # 2: IFR estimation
    # a: create binary image
    image = binary_image(x_ptfr)
    # b: component linking
    components = component_linking(image)

    # 3: multivariate window STFT

def ptfr(x, fs, win_len, sigma):
    win = gaussian(win_len, sigma * win_len)
    f, t, Zxx = stft(x, fs=fs, window=win, nperseg=win_len, noverlap=(win_len-1))

    Zxx = Zxx.transpose()

    return Zxx, f, t

"""
Abdoush, Y., Pojani, G., & Corazza, G. E. (2019).
Adaptive instantaneous frequency estimation of multicomponent signals
based on linear time–frequency transforms.
IEEE Transactions on Signal Processing, 67(12), 3100-3112
"""
def regular_rate(x):
    N = np.shape(x)[0]
    yf = fft(x)
    i_0 = int(- N/2)
    i_max = int(N/2)

    # k_0
    k_0_num = 0
    for k in range(i_0, i_max):
        k_0_num = k_0_num + k * (abs(yf[k]) ** 2)
    k_0_den = 0
    for k in range(i_0, i_max):
        k_0_den = k_0_den + abs(yf[k]) ** 2
    k_0 = k_0_num / k_0_den

    # n_0
    n_0_num = 0
    n_0_den = 0
    for n in range(0, N):
        n_0_num = n_0_num + n * (abs(x[n]) ** 2)
        n_0_den = n_0_den + (abs(x[n]) ** 2)
    n_0 = n_0_num / n_0_den

    # b_eff
    b_eff = 0
    for k in range(i_0, i_max):
        b_temp = ((k - k_0) ** 2) * (abs(yf[k]) ** 2)
        b_eff = b_eff + b_temp

    # t_eff
    t_eff = 0
    for n in range(0, N):
        t_eff = t_eff + (n - n_0) ** 2 * (abs(x[n]) ** 2)

    # v_0
    v_0 = (b_eff / (t_eff * N)) ** 0.5

    return v_0

def test_signal(type="sinusoidal", noise=False):
    fs = 200
    duration = 10

    f_1 = 0.611
    f_2 = 3
    f_3 = 7

    t = np.linspace(0, duration, fs*duration)
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

    if (type == "sinusoidal"):
        signal[start_1:stop_1] = s_1
        signal[start_2:stop_2] = s_2
        signal[start_3:stop_3] = s_3
    elif (type == "time bins"):
        signal[start_1:stop_1] = np.where(s_1>=amp_1*0.9, 0.5, 0)
        signal[start_2:stop_2] = np.where(s_2>=amp_2*0.9, 1, 0)
        signal[start_3:stop_3] = np.where(s_3>=amp_3*0.9, 0.75, 0)

    if noise:
        signal += np.random.normal(-0.1, 0.01, N)

    plt.plot(t, signal)
    plt.show()

    return signal, fs, t

from scipy.signal import find_peaks

def simple_astft(components, signal, filtered, freq, time_b, args):
    fig, ax = plt.subplots()

    t_start = time_b[0]
    t_end = time_b[-1]

    N = len(signal)
    t = np.arange(t_start, t_end, (t_end-t_start)/N, dtype=float)

    ax.plot(t, signal)

    if filtered is not None:
        ax.plot(t, filtered)
        signal = filtered

    for i in components:
        start = i[0][0]
        end = i[0][1] + 1
        window = signal[start:end]

        yf = fft(window)

        n = len(yf)
        freq_arr = freq * np.arange(0, n) / n
        ind = z_score(yf, freq_arr, args)[0]
        #ind = find_peaks(yf)[0]

        for i in ind:
            array = np.zeros(len(yf), dtype=np.complex128)
            array[i] = yf[i]

            yif = ifft(array)
            ax.plot(t[start:end], yif)

    plt.show()
