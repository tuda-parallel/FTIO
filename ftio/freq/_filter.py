import numpy as np
from argparse import Namespace
from rich.panel import Panel
from scipy.signal import butter, filtfilt, lfilter
from ftio.freq.helper import MyConsole
from ftio.plot.plot_filter import plot_filter_results

def filter_signal(args: Namespace, b: np.ndarray) -> np.ndarray:
    """
    Applies a filter (low-pass, high-pass, or band-pass) to the input signal `b` based on `args`.
    
    Parameters:
    - args: Namespace containing filter type and parameters.
        - args.filter_type: str, one of ['lowpass', 'highpass', 'bandpass']
        - args.filter_cutoff: float or tuple, cutoff frequency for low/high-pass filters, or (low, high) for bandpass
        - args.filter_order: int, order of Butterworth filter (default: 4)
    - b: np.ndarray, input signal.
    
    Returns:
    - np.ndarray, filtered signal.
    """
    
    f_n = args.freq / 2  # Nyquist frequency

    if args.filter_type == 'lowpass':
        # Butterworth filter expects a normalized cutoff in the range [0,1].
        # The Nyquist frequency is half the sampling rate, so dividing by it scales the cutoff properly.
        if not isinstance(args.filter_cutoff, list) or len(args.filter_cutoff) != 1 or not isinstance(args.filter_cutoff[0], float):
            raise ValueError("filter_cutoff must be a list containing a single float value.")

        normal_cutoff = args.filter_cutoff[0] / f_n  # Extract the float and normalize
        b_coeff, a_coeff = butter(args.filter_order, normal_cutoff, btype='low', analog=False)

    elif args.filter_type == 'highpass':
        if not isinstance(args.filter_cutoff, list) or len(args.filter_cutoff) != 1 or not isinstance(args.filter_cutoff[0], float):
            raise ValueError("filter_cutoff must be a list containing a single float value.")

        normal_cutoff = args.filter_cutoff[0] / f_n  # Extract the float and normalize
        b_coeff, a_coeff = butter(args.filter_order, normal_cutoff, btype='high', analog=False)

    elif args.filter_type == 'bandpass':
        # Bandpass requires both low and high cutoff frequencies.
        if not isinstance(args.filter_cutoff, (list, tuple)) or len(args.filter_cutoff) != 2:
            raise ValueError("For bandpass, filter_cutoff must be a list or tuple with two values (low_cutoff, high_cutoff).")

        # Normalize both frequencies by Nyquist
        normal_cutoff = [freq / f_n for freq in args.filter_cutoff]
        b_coeff, a_coeff = butter(args.filter_order, normal_cutoff, btype='bandpass', analog=False)

    else:
        raise ValueError("Unsupported filter type. Choose from 'lowpass', 'highpass', or 'bandpass'.")

    # Choose filtering method
    method = "filtfilt"  # Set to "lfilter" if forward filtering is preferred

    if method == "filtfilt":
        # Apply forward and backward filtering to remove phase shift
        filtered_signal = filtfilt(b_coeff, a_coeff, b)
    elif method == "lfilter":
        # Apply only forward filtering (faster but may introduce phase shift)
        filtered_signal = lfilter(b_coeff, a_coeff, b)
    else:
        raise ValueError("Invalid filter method selected. Use 'lfilter' or 'filtfilt'.")

    text = (
        f"- Type: {display_order(args.filter_order)}-order {args.filter_type}\n"
        f"- Cutoff: {', '.join(map(str, args.filter_cutoff))}\n"
        f"- Method: {method}"
        )
    console = MyConsole(args.verbose)
    console.print(
        Panel.fit(
            text,
            style="white",
            border_style="red",
            title="Filtering",
            title_align="left",
        )
    )

    plot_filter_results(args,b,filtered_signal)

    return filtered_signal


def display_order(order):
    if order == 1:
        return "1st"
    elif order == 2:
        return "2nd"
    elif order == 3:
        return "3rd"
    else:
        return f"{order}th"

