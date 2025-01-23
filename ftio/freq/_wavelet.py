""" Wavelet functions (continuous and discrete) 
"""

import numpy as np
import pywt
from scipy import signal
import matplotlib.pyplot as plt


def wavelet_cont(b_sampled, wavelet, level, freq):
    """Continuous wavelet transformation

    Args:
        b_sampled (_type_): _description_
        wavelet (_type_): _description_
        level (_type_): _description_
        freq (_type_): _description_

    Returns:
        _type_: _description_
    """
    # Continues wavelet:
    n = len(b_sampled)
    if isinstance(level, str) and "auto" in level:
        level = pywt.dwt_max_level(n, wavelet)  # pywt.dwt_max_level(n,wavelet)
    else:
        level = int(level)

    print("    '-> \033[1;32mDecomposition level is %d\033[1;0m" % level)
    # [coefficients, frequencies] = pywt.cwt(b_sampled, np.arange(1,5), 'morl')
    # scale = pywt.frequency2scale('morl', np.array([1,10,100])/freq)
    # scale = pywt.frequency2scale('morl', np.arange(freq/100,freq)/freq)
    # scale = 2**np.arange(0,level) #2** mimcs the DWT
    scale = np.arange(1, level)  # 2** mimcs the DWT
    check_wavelet(wavelet, "continuous")
    print(pywt.scale2frequency(wavelet, scale) / (1 / freq))

    [coefficients, frequencies] = pywt.cwt(
        b_sampled, scale, wavelet, sampling_period=1 / freq
    )
    return coefficients, frequencies, scale


def wavelet_disc(b_sampled, wavelet, level):
    # Discrete Wavelet:
    check_wavelet(wavelet, "discrete")
    if isinstance(level, str) and "auto" in level:
        level = pywt.dwt_max_level(
            len(b_sampled), wavelet
        )  # pywt.dwt_max_level(n,wavelet)
    else:
        level = int(level)
    print("    '-> \033[1;32mDecomposition level is %d\033[1;0m" % level)
    coffs = pywt.wavedec(b_sampled, wavelet, level=level)
    return coffs


def check_wavelet(wavelet, mode="discrete"):
    """check that the wavelet selected is supported

    Args:
        wavelet (str): wavelet name
        mode (str, optional): Wavelet mode. Defaults to "discrete".

    Raises:
        Exception: exits the program on unsupported mode
    """
    check = False
    for supported_wavelet in pywt.wavelist(kind=mode):
        if wavelet == supported_wavelet:
            check = True
            break
    if check is False:
        raise ValueError(
            f"Unsupported wavelet specified, supported modes are: {pywt.wavelist(kind=mode)}\nsee: https://pywavelets.readthedocs.io/en/latest/ref/wavelets.html "
        )
        # sys.exit()
    else:
        return


def welch(b, freq):
    """Welch method for spectral density estimation.

    Args:
        b (list[float]): bandwidth over time
        freq (float): sampling frequency
    """
    # f, pxx_den = signal.welch(b, freq, 'flattop', 10000, scaling='spectrum', average='mean')
    f, pxx_den = signal.welch(
        b, freq, "flattop", freq * 256, scaling="spectrum", average="mean"
    )
    plt.semilogy(f, np.sqrt(pxx_den))
    plt.xlabel("frequency [Hz]")
    # plt.ylabel('PSD [V**2/Hz]')
    plt.ylabel("Linear spectrum [V RMS]")
    plt.show()
