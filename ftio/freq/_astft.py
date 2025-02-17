"""
TODO:
OASTFT
- use correct fs in stft
- upgrade to ShortTimeFFT
"""

import math
import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft
from scipy.signal import stft
from scipy.signal.windows import gaussian
from ftio.freq.if_comp_separation import binary_image, component_linking
from ftio.freq.concentration_measures import cm3, cm4, cm5

def astft(b_sampled, freq, bandwidth, time_b):
    test = test_signal()
    #oastft(test)
    astft_mnm(test)

# mix & match
def astft_mnm(signal):
    win_len = cm3(signal)

    # sigma
    sigma = int(win_len / 2.35482)

    signal_tfr = ptfr(signal, win_len, sigma)

    image = binary_image(signal_tfr)
    component_linking(image)

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
    component_linking(image)

    # 3: multivariate window STFT

def ptfr(x, win_len, sigma):
    win = gaussian(win_len, sigma * win_len)
    f, t, Zxx = stft(x, fs=1, window=win, nperseg=win_len, noverlap=(win_len-1))

    Zxx = Zxx.transpose()

    return Zxx

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

def test_signal():
    len = 1024
    x = np.zeros((len,), dtype=np.float32)

    T = len
    fs = 4/T
    t = np.arange(1,T+1)/T
    freqs = 2*np.pi*(t-0.5-fs)/(fs)

    f_1 = 20
    f_2 = 50

    x1 = 1.3*(np.cos(2*np.pi*f_1*t[33:450]))
    x[33:450] = x1
    x2 = 1.1*(np.cos(2*np.pi*f_2*t[650:797]))
    x[650:797] = x2

    fig, ax = plt.subplots()
    ax.plot(t,x)
    plt.show()

    return x