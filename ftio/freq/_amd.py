import numpy as np
import matplotlib.pyplot as plt
from vmdpy import VMD
from pysdkit import EFD

from ftio.freq.anomaly_detection import z_score
from ftio.freq.denoise import tfpf_wvd
from ftio.freq.frq_verification import pcc, scc
from scipy.signal import hilbert

plot = True

def amd(b_sampled, freq, bandwidth, time_b, args, method="vmd"):
    t_start = time_b[0]
    t_end = time_b[-1]
    N = len(b_sampled)
    t = np.linspace(t_start, t_end, N)

    method = "vmd"

    if (method == "vmd"):
        vmd(b_sampled, t, freq, args, denoise=False)

    if (method == "efd"):
        efd(b_sampled, t, freq, args, denoise=True)

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

        components = imf_selection(signal_hat, u_periodic, t, cen_freq_per, fs, args)
    else:
        u, u_hat, omega = VMD(signal, alpha, tau, K, DC, init, tol)

        plot_imfs(signal, t, u, K)

        plot_imf_char(signal, t, fs, u, K)

        center_freqs = omega[-1] * fs
        u_periodic, cen_freq_per = rm_nonperiodic(u, center_freqs, t)

        components = imf_selection(signal, u_periodic, t, cen_freq_per, fs, args)

    remove_zero(components, u_periodic)

    plt.plot(t, signal)

    for p in components:
        start = p[0][0]
        end = p[0][1]
        imf = u_periodic[p[1]]

        #plt.plot(t[start:end], imf[start:end], label=center_freqs[p[1]])
        plt.plot(t[start:end], imf[start:end], label=p[2])
    plt.legend()
    plt.show()

    #rel = imf_select_msm(signal, u_periodic)

    #analytic_signal = hilbert(u[1])
    #amplitude_envelope = np.abs(analytic_signal)

def efd(signal, t, fs, args, denoise=False):
    numIMFs = 10
    efd = EFD(max_imfs=numIMFs)

    # match modes to time windows
    # sinusoidal -> does not work
    # match highest energy contribution

    if denoise:
        signal_hat = tfpf_wvd(signal, fs, t)
        signal_hat = tfpf_wvd(signal_hat, fs, t)

        imfs, cerf = efd.fit_transform(signal_hat, return_all=True)
        plot_imfs(signal, t, imfs, numIMFs, signal_hat)
        print(cerf)

        u_periodic, cen_freq_per = rm_nonperiodic(imfs, cerf, t)

        components = imf_selection(signal_hat, u_periodic, t, cerf, fs, args)

    else:
        imfs, cerf = efd.fit_transform(signal, return_all=True)
        plot_imfs(signal, t, imfs, numIMFs)
        print(cerf)

        u_periodic, cen_freq_per = rm_nonperiodic(imfs, center_freqs, t)

        components = imf_selection(signal, u_periodic, t, cen_freq_per, fs, args)

    remove_zero(components, u_periodic)

    plt.plot(t, signal)

    for p in components:
        start = p[0][0]
        end = p[0][1]
        imf = u_periodic[p[1]]

        #plt.plot(t[start:end], imf[start:end], label=center_freqs[p[1]])
        plt.plot(t[start:end], imf[start:end], label=p[2])
    plt.legend()
    plt.show()


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
    fig, ax = plt.subplots(K+1,3)
    ax[0][0].plot(t, signal)

    for i in range(1,K+1):
        analytic_signal = hilbert(u[i-1])
        amplitude_envelope = np.abs(analytic_signal)
        instantaneous_phase = np.unwrap(np.angle(analytic_signal))
        instantaneous_frequency = np.diff(instantaneous_phase) / (2.0*np.pi) * fs

        if len(u[i-1]) < len(t):
            end = len(u[i-1])
        else:
            end = len(t)

        ax[i][0].plot(t[:end], u[i-1])
        ax[i][1].plot(t[1:end], instantaneous_frequency, label="inst freq")
        ax[i][2].plot(t[:end], amplitude_envelope, label="amp")

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
    from scipy.fft import fft, ifft
    # case 1: equals center frq
    yf = fft(imf)

    ind = np.argmax(np.abs(yf)[1:])+1

    frq_arr = np.zeros(len(imf), dtype="complex")
    frq_arr[ind] = yf[ind]
    
    if (yf[ind-1] > yf[ind-2] and yf[ind-1] > yf[ind+1]):
        frq_arr[ind-1] = yf[ind-1]
    elif (yf[ind+1] > yf[ind+2] and yf[ind+1] > yf[ind-1]):
        frq_arr[ind+1] = yf[ind+1]
    print(frq_arr[ind])
    amp = ifft(frq_arr)

    

    corr = scc(imf, amp).statistic
    print(corr)

    t = np.arange(0, len(imf))
    plt.plot(t, imf)
    plt.plot(t, amp)
    plt.show()

    N = len(imf)
    n_pad = N // 10

    imf_padded = np.pad(imf, (n_pad, n_pad), 'reflect')

    analytic_signal = hilbert(imf_padded)
    amplitude_envelope = np.abs(analytic_signal)
    instantaneous_phase = np.unwrap(np.angle(analytic_signal))
    instantaneous_frequency = np.diff(instantaneous_phase) / (2.0*np.pi) * fs

    

    # recover unpadded
    amp_env = amplitude_envelope[n_pad:-n_pad]
    ifreq = instantaneous_frequency[n_pad:-n_pad]

    fig, ax = plt.subplots(2)
    ax[0].plot(t[:-1], ifreq)
    ax[1].plot(t, amp_env)
    plt.show()

    if (np.std(ifreq) > 0.8):
        print(np.std(ifreq))
        print("removed")
        #return -1

    print("std")
    print(np.std(ifreq))
    print("var")
    print(np.var(ifreq))

    from scipy.fft import fft, ifft

    yf = fft(amp_env)

    # identify peak
    freq_arr = fs * np.arange(0, N) / N
    indices = z_score(yf, freq_arr, args)[0]

    # TODO: argmax? monocomponent, safe some time

    print(indices)

    amp_frq = []
    amp_corr = []

    for ind in indices:
        amp_frq_arr = np.zeros(len(imf), dtype="complex")
        amp_frq_arr[ind] = yf[ind]
        print(amp_frq_arr[ind])
        amp_cos = ifft(amp_frq_arr)

        corr = scc(amp_env, amp_cos).statistic

        if (corr > 0.7):
            return 

        print("corr")
        print(corr)

        #print(type(amp_env[0]))
        #print(type(amp_cos[0]))
        #corr = pcc(amp_env, amp_cos).statistic

        #print("corr")
        #print(corr)

        # plot
        t = np.arange(0, len(imf))
        plt.plot(t, imf)
        plt.plot(t, amp_env)
        plt.plot(t, amp_cos)
        plt.show()

        if corr > 0.8:
            amp_frq.append(fs * ind / len(imf))
            amp_corr.append(corr)
            print("corr segm amp envel & cos > 0.8")
            print(amp_frq)

    if not amp_frq:
        print("center frq")
        print(center_frq)
        return center_frq
    elif len(amp_frq) == 1:
        print("amp frq")
        return amp_frq[0]
    else:
        print("ith amp frq")
        i = np.argmax(amp_corr)
        return amp_frq[i]


def det_imf_frq_old(imf, center_frq, fs, args):
    analytic_signal = hilbert(imf)
    amplitude_envelope = np.abs(analytic_signal)
    instantaneous_phase = np.unwrap(np.angle(analytic_signal))
    instantaneous_frequency = np.diff(instantaneous_phase) / (2.0*np.pi) * fs

    from scipy.fft import fft, ifft

    yf = fft(amplitude_envelope)
    """
    N = len(imf)
    T = 1.0 / 20.0
    xf = np.linspace(0.0, 1.0/(2.0*T), N//2)

    yf2 = fft(imf)

    plt.plot(xf[:40], 2.0/N * np.abs(yf[:N//2])[:40])
    plt.plot(xf[:40], 2.0/N * np.abs(yf2[:N//2])[:40])
    plt.show()
    """
    # identify peak
    n = len(yf)
    freq_arr = fs * np.arange(0, n) / n
    indices = z_score(yf, freq_arr, args)[0]

    amp_frq = []
    amp_corr = []

    for ind in indices:
        # correlation ifft & amplitude envelope
        amp_frq_arr = np.zeros(len(imf))
        amp_frq_arr[ind] = yf[ind]
        amp_cos = ifft(amp_frq_arr)

        corr = scc(amplitude_envelope, amp_cos).statistic

        print(fs * ind / len(imf))
        print(corr)

        t = np.arange(0, len(imf))

        from scipy.stats import entropy

        print("entropy")
        print(entropy(instantaneous_frequency))
        print("std")
        print(np.std(instantaneous_frequency))
        print("var")
        print(np.var(instantaneous_frequency))
        
        
        plt.plot(t, imf)
        plt.plot(t, amplitude_envelope)
        plt.plot(t, amp_cos)
        plt.show()

        plt.plot(t[1:], instantaneous_frequency)
        plt.show()

        plt.plot(t, instantaneous_phase)
        plt.show()
        
        #print("corr segm amp envel & cos")
        #print(corr)

        if corr > 0.8:


            amp_frq.append(fs * ind / len(imf))
            amp_corr.append(corr)
            print("corr segm amp envel & cos > 0.8")
            print(amp_frq)

    if not amp_frq:
        yf = fft(imf)
        peak = np.argmax(np.abs(yf)[1:])
        est_imf_freq = peak * fs / len(imf)
        """
        print(est_imf_freq)
        print(center_frq)
        """
        print("not amp frq")
        return center_frq
    elif len(amp_frq) == 1:
        print("amp frq")
        return amp_frq[0]
    else:
        print("ith amp frq")
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
        if (peak == 0):
            # not periodic
            continue
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
        skip = int(est_per * overlap)
        while(ind+win_size < len(imf)):
            corr = pcc(signal[ind:ind+win_size], imf[ind:ind+win_size]).statistic
            if(corr > 0.65):
                plt.plot(t[ind:ind+win_size], imf[ind:ind+win_size])
            if (corr > 0.65 and not flag):
                start = ind
                comp_counter += 1
                flag = True
            elif(corr <= 0.65 and flag):
                print("not corr")
                print(per_segments)
                #print(per_segments[-1].index)
                # TODO: find better solution
                if(per_segments):
                    print("exists")
                    print(per_segments[-1].index)
                if (per_segments and j == per_segments[-1].index and start < per_segments[-1].end):
                        old_start = per_segments[-1].start
                        del per_segments[-1]
                        comp = component(j, old_start, ind+win_size-skip)
                        per_segments.append(comp)
                else:
                    comp = component(j, start, ind+win_size-skip)
                    per_segments.append(comp)
                start = 0
                flag = False
            ind += skip
        if (flag):
            flag = False
            stop = len(imf)
            if (per_segments and j == per_segments[-1].index and start < per_segments[-1].end):
                old_start = per_segments[-1].start
                del per_segments[-1]
                comp = component(j, old_start, stop)
                per_segments.append(comp)
            else:
                comp = component(j, start, stop)
                per_segments.append(comp)
        plt.show()

    return per_segments


def imf_selection(signal, u_per, t, center_freqs, fs, args): #, u_per):
    signal = signal.astype(float)

    confirmed_win = []
    """
    for j in range(0, u_per.shape[0]):
        imf = u_per[j]

        corr = pcc(signal.astype(float), imf).statistic
        print(corr)
        corr2 = scc(signal.astype(float), imf).statistic
        print(corr2)
        # TODO: check all modes? choose best?
        if corr > 0.65:
            est_frq = det_imf_frq(imf, center_freqs[j], fs, args)
            est_per_time = 1 / est_frq
            duration = t[-1] - t[0]

            if duration > (3*est_per_time*0.9):
                # good enough, no cwindowed correlation checks required
                # single imf describes whole signal
                time = 0, len(imf)
                comp = time, j,  est_frq
                confirmed_win.append(comp)

                return confirmed_win

    import sys
    sys.exit()
    """


    per_segments = imf_select_windowed(signal, t, u_per, fs)
    print("per segments")
    print(per_segments)
    print(len(per_segments))

    for comp in per_segments:
        print(comp)
        imf = u_per[comp.index][comp.start:comp.end]

        est_frq = det_imf_frq(imf, center_freqs[comp.index], fs, args)
        if (est_frq == -1):
            continue
        est_per_time = 1 / est_frq
        duration = t[comp.end-1] - t[comp.start]

        print(duration)

        if duration > (3*est_per_time*0.9):
            time = comp.start, comp.end
            comp = time, comp.index,  est_frq
            confirmed_win.append(comp)

    print("confirmed win")
    print(confirmed_win)

    return confirmed_win

def remove_zero(components, u_per):

    #for comp in components:
    for i in range(0, len(components)):
        imf = u_per[components[i][1]][components[i][0][0]:components[i][0][1]]
        analytic_signal = hilbert(imf)
        amplitude_envelope = np.abs(analytic_signal)

        median_amp = np.median(amplitude_envelope)

        # TODO: arbitrary threshold
        rel_ind = np.nonzero(amplitude_envelope > median_amp*0.5)
        for subarray in rel_ind:
            if (len(subarray) < len(imf)):
                if subarray[0] > 0:
                    imf = imf[subarray[0]:]
                    time = components[i][0][0]+subarray[0], components[i][0][1]
                    components[i] = time, components[i][1], components[i][2]
            # end not removed because of predictions and known boundary limitations
            # TODO: handle arrays req to split




