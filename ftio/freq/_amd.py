from collections import namedtuple
import numpy as np
import matplotlib.pyplot as plt
from vmdpy import VMD
from pysdkit import EFD

from ftio.freq._astft import check_3_periods, simple_astft
from ftio.freq.anomaly_detection import z_score
from ftio.freq.denoise import tfpf_wvd
from ftio.freq.frq_verification import pcc, scc
from scipy.fft import fft, ifft
from scipy.signal import hilbert


plot = True

def amd(b_sampled, freq, bandwidth, time_b, args, method="vmd"):
    """
    Identify periodic time windows with adaptive mode decomposition.
    """
    t_start = time_b[0]
    t_end = time_b[-1]
    N = len(b_sampled)
    t = np.linspace(t_start, t_end, N)

    method = "efd"

    if (method == "vmd"):
        vmd(b_sampled, t, freq, args, denoise=True)

    if (method == "efd"):
        efd(b_sampled, t, freq, args, denoise=False)

def vmd(signal, t, fs, args, denoise=False):
    """
    Variational Mode Decomposition (VMD) based periodicity detection.

    Parameters:
    - signal: np.ndarray, input signal in the time domain.
    - t: np.ndarray, time samples.
    - fs: float, sampling frequency.
    - denoise: bool, whether to apply TFPF.
    """
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

    print(components)

    plt.plot(t, signal)
    for p in components:
        start = p[0][0]
        end = p[0][1]
        imf = u_periodic[p[1]]

        plt.plot(t[start:end], imf[start:end], label=round(p[2], 6))

    plt.legend()
    plt.show()

Component = namedtuple("Component", ["start", "end", "amp", "freq", "phase"])
per_comp = []

def efd(signal, t, fs, args, denoise=False):
    """
    Empirical Fourier decomposition (EFD) based periodicity detection.

    Parameters:
    - signal: np.ndarray, input signal in the time domain.
    - t: np.ndarray, time samples.
    - fs: float, sampling frequency.
    - denoise: bool, whether to apply TFPF.
    """

    numIMFs = 8
    efd = EFD(max_imfs=numIMFs)

    signal_hat = None
    if denoise:
        signal_hat = tfpf_wvd(signal, fs, t)
        signal_hat = tfpf_wvd(signal_hat, fs, t)

        imfs, cerf = efd.fit_transform(signal_hat, return_all=True)
        plot_imfs(signal, t, imfs, numIMFs, signal_hat)
    else:
        imfs, cerf = efd.fit_transform(signal, return_all=True)
        plot_imfs(signal, t, imfs, numIMFs)

    # match modes to time windows
    # sinusoidal -> does not work
    # match highest energy contribution

    # updated center freq
    from scipy.fft import fft,ifft
    cerf2 = np.empty(numIMFs)
    for i in range (0, numIMFs):
        yf = fft(imfs[i])
        ind = np.argmax(np.abs(yf[1:])) + 1
        cerf2[i] = (ind * fs) / len(imfs[i])

        frq_arr = np.zeros(len(imfs[i]), dtype=complex)
        frq_arr[ind] = yf[ind]
        iyf = ifft(frq_arr)

    per_segments = energy_windowed(t, imfs, cerf2, fs)

    # collect potential components
    pot_comp = []

    duration = t[-1] - t[0]
    for p in per_segments:
        # i start stop

        est_frq = cerf2[p.index]
        est_period_time = 1/cerf2[p[0]] #/ fs
        est_period = len(imfs[0]) * (est_period_time/duration)

        length = len(imfs[p[0]][p[1]:p[2]])
        if (length > est_period*3*0.9):
            # remove harmonics
            start = p[1]
            end = start + 3*est_period
            while(end+est_period < p[2]):
                end = end+est_period
            end = end.astype(int)

            if denoise:
                yf = fft(signal_hat[start:end])
            else:
                yf = fft(signal[start:end])

            N = end-start
            freq_arr = fs * np.arange(0, N) / N
            indices = z_score(yf, freq_arr, args)[0]

            exp_frq_bin = (cerf2[p[0]] * N) / fs
            exp_frq_bin = np.round(exp_frq_bin).astype(int)

            for i in indices:
                arr = np.zeros(N, dtype=complex)
                arr[i] = yf[i]
                iyf = ifft(arr)

                if (exp_frq_bin == i or exp_frq_bin-1 == i or exp_frq_bin+1 == i):
                    # collect potential components
                    time = p[1], p[2]
                    c = time, est_frq, est_frq, p[0]
                    pot_comp.append(c)

                    break

    # apply astft
    res = simple_astft(pot_comp, signal, signal_hat, fs, t, args, merge=False, imfs=imfs)
    print(res)

def plot_imfs(signal, t, u, K, denoised=None):
    """
    Plot obtained modes.

    Parameters:
    - signal: np.ndarray, input signal in the time domain.
    - t: np.ndarray, time samples.
    - u: np.ndarray, intrinsic mode functions.
    - K: int, number of modes.
    """
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
    """
    Plot instantaneous frequency and amplitude envelope.

    Parameters:
    - signal: np.ndarray, input signal in the time domain.
    - t: np.ndarray, time samples.
    - fs: float, sampling frequency.
    - u: np.ndarray, intrinsic mode functions.
    - K: int, number of modes.
    """
    fig, ax = plt.subplots(K+1,3)
    ax[0][0].plot(t, signal)

    N = len(u[0])
    n_pad = N // 10

    for i in range(1,K+1):
        imf_padded = np.pad(u[i-1], (n_pad, n_pad), 'reflect')
        analytic_signal = hilbert(imf_padded)
        amplitude_envelope = np.abs(analytic_signal)
        instantaneous_phase = np.unwrap(np.angle(analytic_signal))
        instantaneous_frequency = np.diff(instantaneous_phase) / (2.0*np.pi) * fs

        amp = amplitude_envelope[n_pad:-n_pad]
        ifreq = instantaneous_frequency[n_pad:-n_pad]

        if len(u[i-1]) < len(t):
            end = len(u[i-1])
        else:
            end = len(t)

        ax[i][0].plot(t[:end], u[i-1])
        ax[i][1].plot(t[1:end], ifreq, label="inst freq")
        ax[i][2].plot(t[:end], amp, label="amp")

    plt.legend()
    plt.show()

def rm_nonperiodic(u, center_freqs, t):
    """
    Remove trend component.

    Parameters:
    - u: np.ndarray, intrinsic mode functions.
    - center_freqs: np.ndarray, center frequencies of modes.
    - t: np.ndarray, time samples.
    """
    duration = t[-1] - t[0]

    min_period = duration / 2
    min_frq = (1 / min_period)

    i = 0
    while(center_freqs[i] < min_frq):
        i += 1
    u_periodic = u[i:]

    return u_periodic, center_freqs[i:]

def det_imf_frq(imf, center_frq, fs, args):
    """
    Determine frequence of IMF.

    Parameters:
    - imf: np.ndarray, intrinsic mode function.
    - center_frq: float, center frequencies of modes.
    - fs: float, sampling frequency.
    """
    from scipy.fft import fft, ifft
    #########################################################
    # case 3 & 4: non-stationary
    N = len(imf)
    if N > 10:
        n_pad = N // 10
    else:
        n_pad = 3

    imf_padded = np.pad(imf, (n_pad, n_pad), 'reflect')

    analytic_signal = hilbert(imf_padded)
    amplitude_envelope = np.abs(analytic_signal)
    instantaneous_phase = np.unwrap(np.angle(analytic_signal))
    instantaneous_frequency = np.diff(instantaneous_phase) / (2.0*np.pi) * fs

    # recover unpadded
    amp_env = amplitude_envelope[n_pad:-n_pad]
    ifreq = instantaneous_frequency[n_pad:-n_pad]

    if (np.std(ifreq) > 0.04):
        return -1

    #########################################################
    # case 1: equals center frq
    yf = fft(imf)

    ind = np.argmax(np.abs(yf)[1:])+1
    frq_arr = np.zeros(len(imf), dtype="complex")
    frq_arr[ind] = yf[ind]
    frq_est = ind * fs / len(imf)
    
    if (np.abs(yf[ind-1]) > np.abs(yf[ind-2]) and np.abs(yf[ind-1]) > np.abs(yf[ind+1])):
        frq_arr[ind-1] = yf[ind-1]
        frq_est_2 = (ind-1) * fs / len(imf)
        frq_weighted = frq_est*np.abs(yf[ind]) + frq_est_2*np.abs(yf[ind-1])
        frq_est = frq_weighted / (np.abs(yf[ind]) + np.abs(yf[ind-1]))
    elif (np.abs(yf[ind+1]) > np.abs(yf[ind+2]) and np.abs(yf[ind+1]) > np.abs(yf[ind-1])):
        frq_arr[ind+1] = yf[ind+1]
        frq_est_2 = (ind+1) * fs / len(imf)
        frq_weighted = frq_est*np.abs(yf[ind]) + frq_est_2*np.abs(yf[ind+1])
        frq_est = frq_weighted / (np.abs(yf[ind]) + np.abs(yf[ind+1]))
    amp = ifft(frq_arr)

    corr = scc(imf, amp).statistic

    if corr > 0.8:
        return frq_est

    #########################################################
    # case 2 multiple
    from scipy.fft import fft, ifft
    yf = fft(amp_env)

    # identify peak
    freq_arr = fs * np.arange(0, N) / N
    indices = z_score(yf, freq_arr, args)[0]

    for ind in indices:
        amp_frq_arr = np.zeros(len(imf), dtype="complex")
        amp_frq_arr[ind] = yf[ind]
        amp_cos = ifft(amp_frq_arr)

        corr = scc(amp_env, amp_cos).statistic

        if corr > 0.8:
            return fs * ind / len(imf)

    return -1

from collections import namedtuple
component = namedtuple('component', ['index', 'start', 'end'])

def imf_select_windowed(signal, t, u_per, fs, overlap=0.5):
    """
    Select relevant IMFs by selecting strongly correlated time windows.

    Parameters:
    - signal: np.ndarray, input signal in the time domain.
    - t: np.ndarray, time samples.
    - u_per: np.ndarray, intrinsic mode function without trend.
    - fs: float, sampling frequency.
    """
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
        flag = False
        skip = int(est_per * overlap)
        while(ind+win_size < len(imf)):
            corr = pcc(signal[ind:ind+win_size], imf[ind:ind+win_size]).statistic
            if (corr > 0.65 and not flag):
                start = ind
                comp_counter += 1
                flag = True
            elif(corr <= 0.65 and flag):
                # TODO: find better solution
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

    return per_segments

def energy_windowed(t, imfs, cerf, fs, overlap=0.5):
    """
    Select relevant IMFs by identifying high energy time windows.

    Parameters:
    - signal: np.ndarray, input signal in the time domain.
    - imfs: np.ndarray, intrinsic mode functions.
    - cerf: np.ndarray, center frequencies of modes.
    - fs: float, sampling frequency.
    """
    duration = t[-1] - t[0]

    # relevant segments in signal
    rel_segments = []
    comp_counter = 0

    for i in range(0, imfs.shape[0]):
    #for i in range(1, imfs.shape[0]):
        energy = np.sum(np.abs(imfs[i])**2)

        est_period_time = 1/cerf[i] #/ fs
        est_period = len(imfs[i]) * (est_period_time/duration)

        win_size = 3 * est_period
        win_size = win_size.astype(int)

        ind = 0
        start = 0
        flag = False
        skip = int(est_period * overlap)
        while(ind+win_size < len(imfs[i])):
            energy_win = np.sum(np.abs(imfs[i][ind:ind+win_size])**2)

            # division causes too small values
            energy_scaled = energy_win*(len(imfs[i])/win_size)

            # another arbitrary threshold
            if (energy_scaled >= energy*0.95 and not flag):
                start = ind
                comp_counter += 1
                flag = True
            elif(energy_scaled < energy*0.95 and flag):
                comp = component(i, start, ind+win_size-skip)
                rel_segments.append(comp)
                start = 0
                flag = False
            ind += skip
        # skip remainder
        # due to end effects behavior at the ends is not always reliable
        if (flag):
            flag = False
            stop = len(imfs[i])
            comp = component(i, start, stop)
            rel_segments.append(comp)


    return rel_segments

def imf_selection(signal, u_per, t, center_freqs, fs, args): #, u_per):
    """
    Select relevant IMFs through correlation (VMD).

    Parameters:
    - signal: np.ndarray, input signal in the time domain.
    - u_per: np.ndarray, intrinsic mode functions without trend.
    - t: np.ndarray, time samples.
    - center_freqs: np.ndarray, center frequencies of modes.
    - fs: float, sampling frequency.
    """
    signal = signal.astype(float)

    confirmed_win = []
    for j in range(0, u_per.shape[0]):
        imf = u_per[j]

        corr = pcc(signal.astype(float), imf).statistic
        # TODO: check all modes? choose best?
        if corr > 0.65:
            start = remove_zero_single_mode(imf)

            est_frq = det_imf_frq(imf[start:], center_freqs[j], fs, args)
            if (est_frq == -1):
                continue
            est_per_time = 1 / est_frq
            duration = t[-1] - t[0]

            if duration > (3*est_per_time*0.9):
                # good enough, no cwindowed correlation checks required
                # single imf describes whole signal
                time = start, len(imf)
                comp = time, j,  est_frq
                confirmed_win.append(comp)

                return confirmed_win

    per_segments = imf_select_windowed(signal, t, u_per, fs)

    for comp in per_segments:
        imf = u_per[comp.index][comp.start:comp.end]

        est_frq = det_imf_frq(imf, center_freqs[comp.index], fs, args)
        if (est_frq == -1):
            # use ASTFT to extract components
            add_comp = []

            time = comp.start, comp.end
            frq = center_freqs[comp.index]
            c = time, frq, frq
            add_comp.append(c)

            # half
            frq_half = center_freqs[comp.index] / 2
            c = time, frq_half, frq_half
            add_comp.append(c)

            # third
            frq_third = center_freqs[comp.index] / 3
            c = time, frq_third, frq_third
            add_comp.append(c)

            res = simple_astft(add_comp, signal, signal, fs, t, args)
            for r in res:
                time = r.start, r.end
                c = time, comp.index, r.freq
                confirmed_win.append(c)
            continue

        est_per_time = 1 / est_frq
        duration = t[comp.end-1] - t[comp.start]

        if duration > (3*est_per_time*0.9):
            time = comp.start, comp.end
            comp = time, comp.index,  est_frq
            confirmed_win.append(comp)

    return confirmed_win

def remove_zero(components, u_per):

    for i in range(0, len(components)):
        imf = u_per[components[i][1]][components[i][0][0]:components[i][0][1]]

        N = len(imf)
        n_pad = N // 10

        imf_padded = np.pad(imf, (n_pad, n_pad), 'reflect')

        analytic_signal = hilbert(imf_padded)
        amplitude_envelope = np.abs(analytic_signal)

        # recover unpadded
        amp_env = amplitude_envelope[n_pad:-n_pad]

        median_amp = np.median(amplitude_envelope)

        # TODO: arbitrary threshold
        rel_ind = np.nonzero(amp_env > median_amp*0.3)
        for subarray in rel_ind:
            if (len(subarray) < len(imf)):
                if subarray[0] > 0:
                    imf = imf[subarray[0]:]
                    time = components[i][0][0]+subarray[0], components[i][0][1]
                    components[i] = time, components[i][1], components[i][2]
            # end not removed because of predictions and known boundary limitations
            # TODO: handle arrays req to split

def remove_zero_single_mode(imf):

    N = len(imf)
    n_pad = N // 10

    imf_padded = np.pad(imf, (n_pad, n_pad), 'reflect')

    analytic_signal = hilbert(imf_padded)
    amplitude_envelope = np.abs(analytic_signal)

    # recover unpadded
    amp_env = amplitude_envelope[n_pad:-n_pad]

    median_amp = np.median(amplitude_envelope)

    # TODO: arbitrary threshold
    rel_ind = np.nonzero(amp_env > median_amp*0.3)
    for subarray in rel_ind:
        if (len(subarray) < len(imf)):
            if subarray[0] > 0:
                return subarray[0]
        # end not removed because of predictions and known boundary limitations
        # TODO: handle arrays req to split
    return 0

