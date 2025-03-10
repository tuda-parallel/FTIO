import numpy as np
from argparse import Namespace
from scipy.signal import butter, filtfilt, lfilter

def filter_signal(args: Namespace, b: np.ndarray, t: np.ndarray) -> np.ndarray:
    """
    Applies a filter (low-pass, high-pass, or band-pass) to the input signal `b` based on `args`.
    
    Parameters:
    - args: Namespace containing filter type and parameters.
        - args.filter_type: str, one of ['lowpass', 'highpass', 'bandpass']
        - args.filter_cutoff: float or tuple, cutoff frequency for low/high-pass filters, or (low, high) for bandpass
        - args.filter_order: int, order of Butterworth filter (default: 4)
    - b: np.ndarray, input signal.
    - t: np.ndarray, time values corresponding to `b`.
    
    Returns:
    - np.ndarray, filtered signal.
    """
    
    f_n = 1 / (2*(t[1] - t[0]))  # Nyquist frequency
    
    if args.filter_type == 'lowpass':
        # Butterworth filter expects a normalized cutoff in the range [0,1].
        # The Nyquist frequency is half the sampling rate, so dividing by it scales the cutoff properly.
        normal_cutoff = args.filter_cutoff / f_n
        b_coeff, a_coeff = butter(args.filter_order, normal_cutoff, btype='low', analog=False)
    
    elif args.filter_type == 'highpass':
        normal_cutoff = args.filter_cutoff / f_n
        b_coeff, a_coeff = butter(args.filter_order, normal_cutoff, btype='high', analog=False)
    
    elif args.filter_type == 'bandpass':
        # Bandpass requires both low and high cutoff frequencies.
        if not isinstance(args.filter_cutoff, (list, tuple)) or len(args.filter_cutoff) != 2:
            raise ValueError("For bandpass, cutoff must be a tuple (low_cutoff, high_cutoff).")
        # Normalize both frequencies by Nyquist
        normal_cutoff = [freq / f_n for freq in args.filter_cutoff]
        b_coeff, a_coeff = butter(args.filter_order, normal_cutoff, btype='bandpass', analog=False)
    
    else:
        # If the filter type is unsupported, raise an error
        raise ValueError("Unsupported filter type. Choose from 'lowpass', 'highpass', or 'bandpass'.")

    # You can explicitly choose which filtering method to use
    method = "filtfilt"  # Set this to "lfilter" if you want to use lfilter instead

    if method == "filtfilt":
        # Apply forward and backward filtering to remove phase shift
        # This ensures no phase distortion, but can be computationally more expensive
        filter_signal = filtfilt(b_coeff, a_coeff, b)
    elif method == "lfilter":
        # Apply only forward filtering, which might introduce phase shift
        # This method is faster, but there might be phase distortion in the filtered signal
        filter_signal = lfilter(b_coeff, a_coeff, b)
    else:
        # Invalid method selection
        raise ValueError("Invalid filter method selected. Use 'lfilter' or 'filtfilt'.")
    
    return filter_signal
