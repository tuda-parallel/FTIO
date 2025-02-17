""" Wavelet functions (continuous and discrete) 
"""

from argparse import Namespace
import numpy as np
import pywt
from scipy import signal
import matplotlib.pyplot as plt
from typing import List

from ftio.freq.helper import MyConsole


def wavelet_cont(b_sampled: np.ndarray, wavelet: str, scale:np.ndarray, freq: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Perform continuous wavelet transformation on a given signal.

    Args:
        b_sampled (np.ndarray): The input signal to be transformed.
        wavelet (str): The type of wavelet to use. E.g., 'morlet', 'cmor', etc.
        level (np.ndarray): array of scales
        freq (float): The sampling frequency of the input signal in Hz.

    Returns:
        tuple[np.ndarray, np.ndarray]: A tuple containing:
            - Coefficients (np.ndarray): The wavelet coefficients obtained after the transformation.
            - Frequencies (np.ndarray): The corresponding frequencies for each scale used in the transformation.
    """
    
    sampling_period = 1 / freq
    console = MyConsole(True)
    # console.print(pywt.scale2frequency(wavelet, scale) / sampling_period)
    coefficients, frequencies = pywt.cwt(
        b_sampled, scale, wavelet,sampling_period
    )

    return coefficients, frequencies


def wavelet_disc(b_sampled: np.ndarray, wavelet: str, level: int) -> List[np.ndarray]:
    """
    Perform a discrete wavelet transformation (DWT) on the input signal.

    Args:
        b_sampled (np.ndarray): The input signal to be transformed as a 1D NumPy array.
        wavelet (str): The type of wavelet to use for the transformation.
        level (int): The decomposition level for the wavelet transformation.

    Returns:
        List[np.ndarray]: A list of NumPy arrays, where each array contains the wavelet coefficients 
        for a specific level of decomposition.
    """
    # Perform Discrete Wavelet Transformation
    coefficients = pywt.wavedec(b_sampled, wavelet, level=level)
    return coefficients


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
        if supported_wavelet in wavelet:
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


def decomposition_level(args: Namespace, n: int) -> int:
    """
    Determine the decomposition level for wavelet transformation.

    Args:
        args (Namespace): Parsed arguments containing `level` and `transformation` attributes.
            - `args.level` (int): Specifies the decomposition level. If set to 0, the level is determined automatically.
            - `args.transformation` (str): Specifies the type of transformation ('wave_cont' for continuous or 'wave_disc' for discrete).
        n (int): The length of the input signal.
        wavelet (str): The wavelet type used for the transformation.

    Returns:
        int: The decomposition level to be used for the wavelet transformation.
    """
    level = args.level
    console = MyConsole(True)
    console.print(f"[green]Decomposition level is {level}[/]")
    
    if args.level == 0:
        if "wave_cont" in args.transformation:
            level = 10
            console.print(f"[green]Decomposition level set to {level}[/]")
        else:
            level = pywt.dwt_max_level(n, args.wavelet)  
            console.print(f"[green]Decomposition level optimally adjusted to {level}[/]")

    if "wave_cont" in args.transformation:
        check_wavelet(args.wavelet, "continuous")
    elif "wave_disc" in args.transformation:
        check_wavelet(args.wavelet, "discrete")
    else:
        pass

    return level
