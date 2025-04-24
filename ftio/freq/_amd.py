import numpy as np
import matplotlib.pyplot as plt
from vmdpy import VMD

from ftio.freq.denoise import tfpf_wvd
from scipy.signal import hilbert

def amd(b_sampled, freq, bandwidth, time_b, method="vmd"):
    t_start = time_b[0]
    t_end = time_b[-1]
    N = len(b_sampled)
    t = np.arange(t_start, t_end, (t_end-t_start)/N, dtype=float)

    if (method == "vmd"):
        vmd(b_sampled, t, freq, denoise=True)

def vmd(signal, t, fs, denoise=False):
    # fixed parameters
    tau = 0.           # noise-tolerance (no strict fidelity enforcement)
    DC = 0             # no DC part imposed
    init = 0           # initialize omegas uniformly
    tol = 1e-7

    # signal dependent parameters
    alpha = 5000       # bandwidth constraint
    K = 8              # # modes

    if denoise:
        signal_hat = tfpf_wvd(signal, fs, t)
        signal_hat = tfpf_wvd(signal_hat, fs, t)
        u, u_hat, omega = VMD(signal_hat, alpha, tau, K, DC, init, tol)

        plot_imfs(signal, t, u, K, signal_hat)
    else:
        u, u_hat, omega = VMD(signal, alpha, tau, K, DC, init, tol)

        plot_imfs(signal, t, u, K)

    plot_imf_char(signal, t, fs, u, K)

    center_freqs = omega[-1] * fs
    u_periodic = rm_nonperiodic(u, center_freqs, t)

def plot_imfs(signal, t, u, K, denoised=None):
    fig, ax = plt.subplots(K+1)
    ax[0].plot(t, signal)

    if denoised is not None:
        ax[0].plot(t, denoised)

    for i in range(1,K+1):
        if len(t) % 2 == 1:
            ax[i].plot(t[:-1], u[i-1])
        else:
            ax[i].plot(t, u[i-1])

    plt.show()

def plot_imf_char(signal, t, fs, u, K, denoised=None):
    fig, ax = plt.subplots(K)
    ax[0].plot(t, signal)

    for i in range(1,K):
        analytic_signal = hilbert(u[0])
        amplitude_envelope = np.abs(analytic_signal)
        instantaneous_phase = np.unwrap(np.angle(analytic_signal))
        instantaneous_frequency = np.diff(instantaneous_phase) / (2.0*np.pi) * fs

        ax[i].plot(t[:-1], u[i])
        ax[i].plot(t[1:-1], instantaneous_frequency, label="inst freq")
        ax[i].plot(t[:-1], amplitude_envelope, label="amp")

    plt.legend()
    plt.show()

def rm_nonperiodic(u, center_freqs, t):
    duration = t[-1] - t[0]

    min_period = duration / 2
    min_frq = (1 / min_period)

    i = 0
    while(center_freqs[i] < min_frq):
        i += 1
    u_periodic = u[i:]

    return u_periodic
