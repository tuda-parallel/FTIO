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
from scipy.signal.windows import gaussian, boxcar
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

    denoise = False

    t_start = time_b[0]
    t_end = time_b[-1]
    N = len(b_sampled)
    t = np.linspace(t_start, t_end, N, dtype=float)

    if denoise:
        signal_hat = tfpf_wvd(b_sampled, freq, t)

    test, fs, time = test_signal("sinusoidal", noise=False)

    #win_len = 200 #cm3(test)
    #print(win_len)
    #plot_tf(test, fs, time, win_len=350, step=0.1)
    #plot_tf(test, fs, time, win_len, nfreqbins=80, step=0.1)
    #astft_mnm(test, fs, time, args)

    astft_mnm(b_sampled, freq, t, args) #, filtered=signal_hat)

    #tf_samp = tfpf_wvd(test, fs, time)
    #plot_tf(tf_samp, fs, time)
    #decomp_vmd(tf_samp, time_b)

# mix & match
def astft_mnm(signal, freq, time_b, args, filtered=None):
    if filtered is None:
        win_len = cm5(signal)
    else:
        win_len = cm5(filtered)

    # sigma
    sigma = int(win_len / 2.35482)

    if filtered is None:
        signal_tfr, f, t = ptfr(signal, freq, win_len, sigma)
    else:
        signal_tfr, f, t = ptfr(filtered, freq, win_len, sigma)

    #image = binary_image_nprom(signal_tfr, n=3)
    image = binary_image_zscore(signal_tfr, freq, args)

    components = component_linking(image, freq, win_len)

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

def check_3_periods(signal, fs, exp_freq, est_period, start, end):
    win_len = (int)(3 * est_period)
    print(win_len)

    # area where component is expected
    # add 1.5, 1 bonus,
    bonus = est_period.astype(int)
    print(bonus)
    _start = start - bonus
    _end = end + bonus
    if _start < 0:
        _start = 0
    if _end > len(signal):
        _end = len(signal)

    subsignal = signal[_start:_end]

    win = boxcar(win_len) #gaussian(stft_win, 1) #, sigma * win_len)
    hop = 1
    f, t, Zxx = stft(subsignal, fs=fs, window=win, nperseg=win_len, noverlap=(win_len - hop))

    exp_frq_bin = (exp_freq * win_len) / fs
    exp_frq_bin = np.round(exp_frq_bin).astype(int)

    comp = []
    flag = False
    start = 0
    # iterate over time instants
    for i in range(0,len(t)):
        yf = Zxx[:exp_frq_bin+3,i].transpose()
        yf = np.abs(yf)
        # check if expected freq is peak
        if (yf[exp_frq_bin] > yf[exp_frq_bin-1] and yf[exp_frq_bin] > yf[exp_frq_bin+1]):
            if not flag:
                start = i
                flag = True
            continue
        # or if expected + neighbor are peak
        # additional peak afterwards
        elif (yf[exp_frq_bin] > yf[exp_frq_bin-1] and yf[exp_frq_bin] > yf[exp_frq_bin+2] and yf[exp_frq_bin+1] > yf[exp_frq_bin-1] and yf[exp_frq_bin+1] > yf[exp_frq_bin+2]):
            if not flag:
                start = i
                flag = True
            continue
        # additional peak before
        elif (yf[exp_frq_bin] > yf[exp_frq_bin+1] and yf[exp_frq_bin] > yf[exp_frq_bin-2] and yf[exp_frq_bin-1] > yf[exp_frq_bin+1] and yf[exp_frq_bin-1] > yf[exp_frq_bin-2]):
            if not flag:
                start = i
                flag = True
            continue
        else:
            if not flag:
                continue
            stop = i
            c = start, stop
            comp.append(c)
            start = 0
            stop = 0
            flag = False
    if flag:
        stop = len(t)-1
        c = start, stop
        comp.append(c)

    final_comp = []
    # check length component
    for c in comp:
        if (c[1]-c[0])*hop >= win_len:
            c = c[0]+_start, c[1]+_start
            final_comp.append(c)

    return final_comp

from scipy.signal import find_peaks

def simple_astft(components, signal, filtered, fs, time_b, args):
    t_start = time_b[0]
    t_end = time_b[-1]

    N = len(signal)
    t = np.arange(t_start, t_end, (t_end-t_start)/N, dtype=float)

    duration = t_end - t_start

    if filtered is not None:
        #ax.plot(t, filtered)
        signal = filtered

    # merge interrupted components
    i = 0
    length = len(components)
    #for i in range(0, length-1):
    while (i < length-1):
        if (components[i][1] == components[i+1][1]):
            est_period_time = 1/components[i][1] #/ fs
            est_period = len(signal) * (est_period_time/duration)

            # end - start
            dist = components[i+1][0][0] - components[i][0][1]
            if (dist < est_period):
                time = components[i][0][0], components[i+1][0][1]
                components[i] = time, components[i][1], components[2] 
                del components[i+1]
                length -= 1
        i += 1

    for i in components:
        start = i[0][0]
        end = i[0][1] + 1
        window = signal[start:end]
        comp_length = i[0][1] - i[0][0]

        # find correct window

        # too long: time smearing
        # too short: peak not dominant enough

        # time
        est_period_time = 1/i[1] #/ fs

        est_period = len(signal) * (est_period_time/duration)

        # skip too short components
        skip_threshold = 0.9
        min_length = 3 * est_period * skip_threshold
        if (comp_length < min_length):
            continue

        # two strategies
        # window 3 periods: everywhere where argmax matches, cant refine frequency
        # window londest possible multiple of periods smaller comp: choose based on magnitude

        # use window with length multiple of bin im period to verify
        # 3 periods: better time resolution
        # worse frq -> advantage, small changes cannot be represented, more robust
        # get final frq afterwards
        final_components = check_3_periods(signal, fs, i[1], est_period, start, end)

        for fc in final_components:
            # retrieve final frq est & functional from longest possible multiple
            start_frq = fc[0]
            period = est_period.astype(int)
            stop_frq = start_frq + 3*period
            while (stop_frq + period < fc[1]):
                stop_frq += period

            # center window
            over = fc[1] - stop_frq
            start_frq += over // 2
            stop_frq += over // 2

            yf = fft(signal[start_frq:stop_frq])

            frqs = np.abs(yf[1:N//2])
            peak = np.argmax(frqs)+1

            #arr = np.zeros(stop_frq-start_frq, dtype="complex")
            #arr[peak] = yf[peak]
            #iyf = ifft(arr)
            #plt.plot(t[start_frq:stop_frq], iyf, label="ifft", linewidth=5)

            amp_final = np.abs(yf[peak]) / (stop_frq - start_frq)
            frq_final = peak * fs / (stop_frq - start_frq)

            # compute phase shift
            # phi = -2 * pi * f * t_shift (no minus because shift to left)
            #phi_shift = -2 * np.pi * frq_final * (t[start_frq]-t[fc[0]])
            phi_shift = - 2 * np.pi * frq_final * (t[start_frq - fc[0]])
            phase_final2 = np.angle(yf[peak] * np.exp(1j*phi_shift))
            phase_final = np.angle(yf[peak])

            # fix phase
            # wrong because of center?

            est_time = t[fc[0]:fc[1]]
            #t_temp = np.linspace(0, t[fc[1]-fc[0]], fc[1]-fc[0], dtype=float)
            #t_temp =  t[fc[0]:fc[1]]-fc[0]
            t_temp = np.linspace(-over//2, (stop_frq-start_frq)+over//2, fc[1]-fc[0], dtype=float)
            t_temp = np.linspace(t[start_frq], t[stop_frq], (stop_frq-start_frq), dtype=float, endpoint=True)

            #t_fc = np.linspace(t[fc[0]], t[fc[1]-1], fc[1]-fc[0], dtype=float, endpoint=True)

            #est_final = amp_final * np.cos(2 * np.pi * frq_final * t_temp + phase_final)
            #est_final = amp_final * np.cos(2 * np.pi * frq_final * t + phase_final)
            #est_final = amp_final * np.cos(2 * np.pi * frq_final * t + phase_final) #- 1j * amp_final * np.sin(2 * np.pi * frq_final * t + phase_final)
            #est_final2 = amp_final * np.cos(2 * np.pi * frq_final * t + phase_final)
            #est_final2 = amp_final * np.cos(2 * np.pi * frq_final * t_temp + phase_final)
            est_final3 = amp_final * np.cos(2 * np.pi * frq_final * t + phase_final2)

            #est_final4 = amp_final * np.cos(2 * np.pi * frq_final * t_fc + phase_final - 1)
            #est_final5 = amp_final * np.cos(2 * np.pi * frq_final * t_fc + phase_final2)

            #est_final2 = amp_final * np.cos(2 * np.pi * frq_final * t_temp + phase_final)

            arr = np.zeros(stop_frq - start_frq)
            arr[peak] = yf[peak]
            iyf = ifft(arr)

            plt.plot(t,signal)
            plt.plot(t[fc[0]:fc[1]], est_final3[0:fc[1]-fc[0]], label="fc, phase shift")
            plt.legend()
            plt.show()

        # longest possible multiple: 
        # -> implement both


        #stft_win = est_period * 3
        #while (stft_win+est_period < comp_length):
        #    stft_win += est_period
        #stft_win = stft_win.astype(int)
        

        # todo: add 1.5 of win len at each side, remove afgertwars 

        #win = boxcar(stft_win) #gaussian(stft_win, 1) #, sigma * win_len)
        #f, t, Zxx = stft(window, fs=fs, window=win, nperseg=stft_win, noverlap=(stft_win-1))

        # find component ~ i[1] frequency
        #exp_frq_bin = (i[1] * stft_win) / fs
        #print(exp_frq_bin)


        #T = 1.0 / 1000.0
        #xf = np.linspace(0.0, 1.0/(2.0*T), N//2)
        #yf = 2.0/N * np.abs(Zxx[104][:N//2])

        #plt.plot(xf, yf)
        #plt.show()

        # create array max values
        #value_max = np.max(np.abs(Zxx)[:][1:], axis=0)
        #print(value_max)

        # create array index max value
        #ind_max = np.argmax(np.abs(Zxx)[:], axis=0)
        #print(ind_max)

        #print(np.abs(Zxx)[:,1])


        # extract components




        # 

        """
        yf = fft(window)

        n = len(yf)
        freq_arr = fs * np.arange(0, n) / n
        ind = z_score(yf, freq_arr, args)[0]
        #ind = find_peaks(yf)[0]

        for i in ind:
            array = np.zeros(len(yf), dtype=np.complex128)
            array[i] = yf[i]

            yif = ifft(array)
            ax.plot(t[start:end], yif)

        print("end")

        continue
        """

    #plt.show()
