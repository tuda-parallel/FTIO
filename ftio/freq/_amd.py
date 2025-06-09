import numpy as np
import matplotlib.pyplot as plt
from vmdpy import VMD

from ftio.freq.denoise import tfpf_wvd
from ftio.freq.frq_verification import pcc, scc
from scipy.signal import hilbert

def amd(b_sampled, freq, bandwidth, time_b, method="vmd"):
    t_start = time_b[0]
    t_end = time_b[-1]
    N = len(b_sampled)
    t = np.linspace(t_start, t_end, N)

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
    u_periodic, cen_freq_per = rm_nonperiodic(u, center_freqs, t)

    #rel = imf_select_msm(signal, u_periodic)

    #analytic_signal = hilbert(u[1])
    #amplitude_envelope = np.abs(analytic_signal)

    imf_select_change_point(signal_hat, u_periodic, t, cen_freq_per)

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
    fig, ax = plt.subplots(K+1)
    ax[0].plot(t, signal)

    for i in range(1,K+1):
        analytic_signal = hilbert(u[i-1])
        amplitude_envelope = np.abs(analytic_signal)
        instantaneous_phase = np.unwrap(np.angle(analytic_signal))
        instantaneous_frequency = np.diff(instantaneous_phase) / (2.0*np.pi) * fs

        if len(u[i-1]) < len(t):
            end = len(u[i-1])
        else:
            end = len(t)

        ax[i].plot(t[:end], u[i-1])
        ax[i].plot(t[1:end], instantaneous_frequency, label="inst freq")
        ax[i].plot(t[:end], amplitude_envelope, label="amp")

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

    return u_periodic, center_freqs[i:]

# most significant mode
def imf_select_msm(signal, u_per):
    corr_stats = np.empty(u_per.shape[0])
    for i in range(0, u_per.shape[0]):
        corr_stats[i] = scc(signal, u_per[i]).statistic

    print(corr_stats)

    best = np.max(corr_stats)
    if best > 0.6:
        ind = np.argmax(corr_stats)
        return u_per[ind]

    """
    else: non-stationary, but possibly stationary in smaller segments
    """

#def imf_select_multiple(signal, u_per):
    # TODO

#def imf_select_windowed(signal, u_per):
    # window length
    # stationary subsignal: imf either ~constant or periodic

import ruptures as rpt

def imf_select_change_point(signal, u_per, t, center_freqs): #, u_per):
    # change point detection
    #model = "l1"
    #model = "l2"
    #model = "normal"
    model = "rbf"
    #model = "cosine"
    #model = "linear"
    #model = "clinear"
    #model = "rank"
    #model = "ml"
    #model = "ar"
    #model = "l1"

    per_segments = []

    for j in range(0, u_per.shape[0]):
        imf = u_per[j]

        corr = pcc(signal.astype(float), imf).statistic
        if corr > 0.7:
            start = 0
            end = len(imf)
            time = start, end

            comp = time, j
            per_segments.append(comp)

            # good enough, no change point detection required
            # single imf describes whole signal
            break

        algo = rpt.Binseg(model=model).fit(imf)
        #result = algo.predict(pen=5)
        result = algo.predict(n_bkps=3)

        #rpt.display(imf, result)
        #plt.show()

        if result[-1] == len(u_per[j]):
            result = np.pad(result, (1,0), constant_values=(0,))
            result[-1] = len(u_per[j])-1
        else:
            result = np.pad(result, (1,1), constant_values=(0, len(u_per[j])-1))
        min_length = (1 / center_freqs[j]) * 2

        for i in range(0, len(result)-1):
            start = result[i]
            end = result[i+1]

            if (t[end] - t[start] < min_length):
                continue

            window = signal[start:end]
            segment = imf[start:end]

            #corr = scc(window, segment).statistic
            corr = pcc(window.astype(float), segment.astype(float)).statistic
            if corr > 0.6:
                time = start, end

                comp = time, j
                per_segments.append(comp)

    if per_segments:
        plt.plot(t, signal)

        for p in per_segments:
            start = p[0][0]
            end = p[0][1]
            imf = u_per[p[1]]

            plt.plot(t[start:end], imf[start:end], label=center_freqs[p[1]])

        plt.legend()
        plt.show()





