"""
TODO:
- scaling parameter mu
- lag window length (21): time or frequency window?
- normalization of max?
- f_p: highest relevant frequency
"""

import math
import numpy as np

from tftb.processing import PseudoWignerVilleDistribution as pwvd
from tftb.processing import smoothed_pseudo_wigner_ville

import matplotlib.pyplot as plt

from scipy.signal.windows import boxcar

"""
Boashash, B., & Mesbah, M. (2004).
Signal enhancement by time-frequency peak filtering.
IEEE Transactions on signal processing, 52(4), 929-937.
"""

def tfpf_wvd(x, fs, time_b):

    # scaling
    x_scaled = scale_signal(x)

    # resample
    # 30-times oversampled

    # encode
    mu = 5 # TODO: don't know, guessed

    z_x = np.zeros((len(x),), dtype=np.complex128)
    sum = 0.0
    for m in range(0, len(x)):
        sum += x_scaled[m]
        z_x[m] = np.exp(1j*2*np.pi*mu*sum)

    # window length
    #tau = (0.634 * fs) / (np.pi * f_peak)

    # lag window: 21 samples
    ts = np.arange(0.0, len(x), 1)

    # PWVD
    twindow = boxcar(209) # random
    fwindow = boxcar(21)
    tfr_wvd = smoothed_pseudo_wigner_ville(x, twindow=twindow, fwindow=fwindow)

    # estimate peak
    x_c_hat = np.max(tfr_wvd, axis=0) / mu
    x_c_hat /= len(x) # normalisation? result too large...

    # recover signal
    x_hat = recover_signal(x, x_c_hat)

    tfpf_wvd_plot(x, x_hat, time_b)

    return x_hat

def scale_signal(x):
    # [0,0.5], arb chosen in "IF estimation for multicomponent signals [..]"
    a = 0.4
    b = 0.1

    x_min = np.min(x)
    x_max = np.max(x)

    scaled = np.zeros((len(x),), dtype=np.complex128)
    for m in range(0,len(x)):
        scaled[m] = (a-b) * (x[m]-x_min) * 1/(x_max-x_min) + b

    return scaled

def recover_signal(x, x_c_hat):
    # [0,0.5], arb chosen in "IF estimation for multicomponent signals [..]"
    a = 0.4
    b = 0.1

    x_min = np.min(x)
    x_max = np.max(x)

    recovered = np.zeros((len(x),), dtype=np.complex128)
    for m in range(0,len(x)):
        recovered[m] = (x_c_hat[m]-b) * (x_max-x_min) * 1/(a-b) + x_min

    return recovered

def tfpf_wvd_plot(x, x_hat, time_b):
    fig, ax = plt.subplots(2)

    t_start = time_b[0]
    t_end = time_b[-1]

    N = len(x)
    t = np.arange(t_start, t_end, (t_end-t_start)/N, dtype=float)

    ax[0].plot(t, x)

    ax[1].plot(t, x)
    ax[1].plot(t, x_hat)

    plt.show()
