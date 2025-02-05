"""
TODO:
OASTFT
- add overlap in PTFR
- use scipy STFT
"""

import math
import numpy as np
from scipy.fft import fft
from scipy import signal

def astft(b_sampled, freq, bandwidth, time_b):
    oastft(b_sampled)

"""
Abdoush, Y., Pojani, G., & Corazza, G. E. (2019).
Adaptive instantaneous frequency estimation of multicomponent signals
based on linear time–frequency transforms.
IEEE Transactions on Signal Processing, 67(12), 3100-3112
"""
def oastft(x):
    # 1: construct a ptfr
    x_ptfr = ptfr(x)

    # 2: IFR estimation

    # 3: multivariate window STFT

def ptfr(x):
    # regular rate, ratio effective bandwidth and effective time duration
    v_0 = regular_rate(x)

    # (3/7)^(1/4) * 1/sqrt(2*pi*v_0)
    sigma = 0.8091067 / (math.sqrt(2 * math.pi * v_0))

    # FWHM: 2*sqrt(2*ln(2))*sigma = 2.35482*sigma
    win_len = int(2.35482 * sigma * len(x))

    # zeropad
    rem = len(x) % win_len
    if (rem != 0):
        x = np.pad(x, (0, win_len-rem), 'constant')

    rows = int(len(x)/win_len)
    output = np.empty(shape=(rows, win_len), dtype=np.complex128)

    # gaussian window
    gauss = signal.windows.gaussian(win_len, sigma*len(x))

    for i in range(0, rows):
        windowed = x[win_len*i:win_len*(i+1)] * gauss
        output[i:] = fft(windowed)

    return output

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
    i_max = int(N/2 - 1)

    # k_0
    k_0_num = 0
    for i in range(i_0, i_max):
        k_0_num = k_0_num + i * (abs(yf[i]) ** 2)
    k_0_den = 0
    for i in range(0, N-1):
        k_0_den = k_0_den + abs(yf[i]) ** 2
    k_0 = k_0_num / k_0_den

    # n_0
    n_0_num = 0
    n_0_den = 0
    for n in range(0, N-1):
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
    for n in range(0, N-1):
        t_eff = t_eff + (n - n_0) ** 2 * (abs(x[n]) ** 2)

    # v_0
    v_0 = b_eff / t_eff

    return v_0