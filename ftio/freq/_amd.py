import numpy as np
import matplotlib.pyplot as plt
from vmdpy import VMD

from ftio.freq.anomaly_detection import z_score
from ftio.freq.denoise import tfpf_wvd
from ftio.freq.frq_verification import pcc, scc
from scipy.signal import hilbert

def amd(b_sampled, freq, bandwidth, time_b, args, method="vmd"):
    t_start = time_b[0]
    t_end = time_b[-1]
    N = len(b_sampled)
    t = np.linspace(t_start, t_end, N)

    if (method == "vmd"):
        vmd(b_sampled, t, freq, args, denoise=True)

def vmd(signal, t, fs, args, denoise=False):
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

        plot_imf_char(signal, t, fs, u, K)

        center_freqs = omega[-1] * fs
        u_periodic, cen_freq_per = rm_nonperiodic(u, center_freqs, t)

        imf_selection(signal, signal_hat, u_periodic, t, cen_freq_per, fs, args)
    else:
        u, u_hat, omega = VMD(signal, alpha, tau, K, DC, init, tol)

        plot_imfs(signal, t, u, K)

        plot_imf_char(signal, t, fs, u, K)

        center_freqs = omega[-1] * fs
        u_periodic, cen_freq_per = rm_nonperiodic(u, center_freqs, t)

        imf_selection(signal, signal, u_periodic, t, cen_freq_per, fs, args)

    #rel = imf_select_msm(signal, u_periodic)

    #analytic_signal = hilbert(u[1])
    #amplitude_envelope = np.abs(analytic_signal)

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

def det_imf_frq(imf, center_frq, fs, args):
    analytic_signal = hilbert(imf)
    amplitude_envelope = np.abs(analytic_signal)

    ####

    instantaneous_phase = np.unwrap(np.angle(analytic_signal))
    instantaneous_frequency = np.diff(instantaneous_phase) / (2.0*np.pi) * fs

    #length = len(imf)
    #if len(instantaneous_frequency) < length:
    #    length = len(instantaneous_frequency)
    #if len(amplitude_envelope) < length:


    t = np.arange(0, len(imf))

    #plt.plot(t, imf)
    #plt.plot(t[1:], instantaneous_frequency, label="inst freq")
    #plt.plot(t, amplitude_envelope, label="amp")

    #plt.show()

    ###

    from scipy.fft import fft, ifft

    yf = fft(amplitude_envelope)

    N = len(imf)
    T = 1.0 / 20.0
    xf = np.linspace(0.0, 1.0/(2.0*T), N//2)

    #plt.plot(xf[:30], 2.0/N * np.abs(yf[:N//2])[:30])
    #plt.show()

    # identify peak
    n = len(yf)
    freq_arr = fs * np.arange(0, n) / n
    indices = z_score(yf, freq_arr, args)[0]

    #ind = indices[0]

    amp_frq = []
    amp_corr = []

    #print("inidices peaks amp env")
    #print(ind)

    for ind in indices:

        # correlation ifft & amplitude envelope
        amp_frq_arr = np.zeros(len(imf))
        amp_frq_arr[ind] = yf[ind]
        amp_cos = ifft(amp_frq_arr)

        corr = scc(amplitude_envelope, amp_cos).statistic

        t = np.arange(0, len(imf))

        #plt.plot(t, amplitude_envelope)
        #plt.plot(t, amp_cos)
        #plt.show()

        print("corr segm amp envel & cos")
        print(corr)

        if corr > 0.8:
            amp_frq.append(fs * ind / len(imf))
            amp_corr.append(corr)
            print("corr segm amp envel & cos > 0.8")
            print(amp_frq)

    if not amp_frq:
        return center_frq
    elif len(amp_frq) == 1:
        return amp_frq[0]
    else:
        i = np.argmax(amp_corr)
        return amp_frq[i]

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

from collections import namedtuple
component = namedtuple('component', ['index', 'start', 'end'])

def imf_select_windowed(signal, t, u_per, fs, overlap=0.5):
    # window length
    # stationary subsignal: imf either ~constant or periodic

    duration = t[-1] - t[0]

    per_segments = []
    comp_counter = 0

    for j in range(0, u_per.shape[0]):
        imf = u_per[j]

        #analytic_signal = hilbert(imf)
        #amplitude_envelope = np.abs(analytic_signal)

        from scipy.fft import fft, ifft
        yf = fft(imf)

        # use max to save comp time, narrow band
        peak = np.argmax(np.abs(yf)[1:])
        est_frq = peak * fs / len(imf)
        est_per_time = 1 / est_frq

        est_per = len(imf) * (est_per_time / duration)
        est_per = est_per.astype(int)

        # arbitrary
        win_size = 3 * est_per
        win_size = win_size.astype(int)

        ind = 0
        start = 0
        plt.plot(t, signal)
        flag = False
        while(ind+win_size < len(imf)):
            corr = pcc(signal[ind:ind+win_size], imf[ind:ind+win_size]).statistic
            if(corr > 0.65):
                plt.plot(t[ind:ind+win_size], imf[ind:ind+win_size])
            if (corr > 0.65 and not flag):
                start = ind
                comp_counter += 1
                flag = True
            elif(corr <= 0.65 and flag):
                comp = component(j, start, ind+win_size)
                per_segments.append(comp)
                start = 0
                flag = False
            ind += int(est_per * overlap)
        if (flag):
            flag = False
            stop = len(imf)
            comp = component(j, start, stop)
            per_segments.append(comp)
        plt.show()

    return per_segments


def imf_selection(orig, signal, u_per, t, center_freqs, fs, args): #, u_per):
    signal = signal.astype(float)

    for j in range(0, u_per.shape[0]):
        imf = u_per[j]

        corr = pcc(signal.astype(float), imf).statistic
        if corr > 0.65:
            est_frq = det_imf_frq(imf, center_freqs[j], fs, args)
            est_per_time = 1 / est_frq
            duration = t[-1] - t[0]

            if duration > (3*est_per_time*0.9):
                plt.plot(t[:len(imf)], imf, label=est_frq)
                plt.show()

            # good enough, no change point detection required
            # single imf describes whole signal
            break

    per_segments = imf_select_windowed(signal, t, u_per, fs)

    confirmed_win = []

    for comp in per_segments:
        imf = u_per[comp.index][comp.start:comp.end]

        est_frq = det_imf_frq(imf, center_freqs[j], fs, args)
        est_per_time = 1 / est_frq
        duration = t[comp.end-1] - t[comp.start]

        if duration > (3*est_per_time*0.9):
            time = comp.start, comp.end

            comp = time, comp.index,  est_frq

            confirmed_win.append(comp)

    if confirmed_win:
        plt.plot(t, orig)

        for p in confirmed_win:
            start = p[0][0]
            end = p[0][1]
            imf = u_per[p[1]]

            #plt.plot(t[start:end], imf[start:end], label=center_freqs[p[1]])
            plt.plot(t[start:end], imf[start:end], label=p[2])

        plt.legend()
        plt.show()





