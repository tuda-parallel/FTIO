"""
TODO:
- make plot pretty
- plot x axis in Hz
- plot y axis in s
- plot global DFT below
- plot plot signal left side
"""

import matplotlib.colors
import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft, ifft
from scipy.signal import stft
from scipy.signal.windows import gaussian, boxcar

from ftio.freq.concentration_measures import cm3,cm4,cm5

def plot_tf(x, fs, time):
    win_len = cm4(x)

    time_steps = 100
    hop = len(x) // time_steps
    sigma = int(win_len / 2.35482)

    win = gaussian(win_len, sigma, sym=False)
    f, t, Zxx = stft(x, fs=fs, window=win, nperseg=win_len, noverlap=(win_len-hop))
    Zxx = Zxx.transpose()

    N = win_len
    T = 1.0 / 300.0
    xf = np.linspace(0.0, 1.0/(2.0*T), 40)

    fig, ax = plt.subplots()

    step = (2.0/N * np.max(abs(Zxx[0]))) / 10

    for i in range(0,time_steps):
        yf = 2.0/N * np.abs(Zxx[i][:40])
        yf_norm = yf / np.max(yf)
        ax.plot(xf[:], yf_norm+step*i, color='black', linewidth=1)

    # x-label
    freq_arr = fs * np.arange(0, N) / N
    xticks = xf[:40:10]
    xlabels = freq_arr[:40:10]
    ax.set_xticks(xticks, labels=xlabels)

    # y-label
    minimum = np.min(2.0/N * np.abs(Zxx[0][:40])) / np.max(2.0/N * np.abs(Zxx[0][:40]))
    maximum = (np.min(2.0/N * np.abs(Zxx[time_steps-1][:40]) / np.max(2.0/N * np.abs(Zxx[time_steps-1][:40]))) +step*(time_steps-1))
    yticks = np.linspace(minimum, maximum, 5, endpoint=True)

    t_start = time[0]
    t_end = time[-1]
    ylabels = np.linspace(t_start, t_end, 5, endpoint=True)

    ax.set_yticks(yticks, labels=ylabels)

    plt.show()

def plot_tf_contour(x, fs, time):
    win_len = cm3(x)
    win = boxcar(win_len)

    hop = 1
    f, t, Zxx = stft(x, fs=fs, window=win, nperseg=win_len, noverlap=(win_len-hop))

    fig, ax = plt.subplots()

    cont = plt.contour(t, f[:80], np.abs(Zxx)[:80,:], 20, cmap='summer')

    # use "continuous" colormap with discrete contour plot
    # https://stackoverflow.com/questions/44498631/continuous-colorbar-with-contour-levels
    norm = matplotlib.colors.Normalize(vmin=cont.cvalues.min(), vmax=cont.cvalues.max())
    sm = plt.cm.ScalarMappable(norm=norm, cmap = cont.cmap)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, ticks=cont.levels[::2])

    plt.title("Time-Frequency Contour Plot")
    plt.xlabel("Time in [s]")
    plt.ylabel("Frequency in [Hz]")

    plt.show()