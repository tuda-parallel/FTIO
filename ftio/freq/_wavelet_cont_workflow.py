"""Contains functions that execute workflow using the continuous Wavelet Transform.
"""
import time
from argparse import Namespace
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from  pywt import frequency2scale

from ftio.freq._wavelet import  wavelet_cont
from ftio.freq._wavelet_helpers import get_scales
from ftio.freq.discretize import sample_data_and_prepare_plots
from ftio.freq.helper import MyConsole
from ftio.plot.plot_wavelet_cont import  plot_wave_cont_and_spectrum, plot_scales, plot_scales_all_in_one # plot_spectrum, plot_wave_cont
from ftio.freq._dft_workflow import ftio_dft
from ftio.prediction.helper import get_dominant_and_conf
# from ftio.freq._logicize import logicize

def ftio_wavelet_cont(args:Namespace, bandwidth: np.ndarray, time_b: np.ndarray, ranks: int = 0):
    """
    Executes continuous wavelet transformation on the provided bandwidth data.

    Args:
        args: The Namespace object containing configuration options.
        bandwidth (np.ndarray): The bandwidth data to process.
        time_b (np.ndarray): The corresponding time points for the bandwidth data.
        ranks (int): The rank value (default is 0).
    """
    #! Default values for variables
    share = {}
    df_out = [[], [], [], []]
    prediction = {
        "source": {args.transformation},
        "dominant_freq": [],
        "conf": [],
        "t_start": 0,
        "t_end": 0,
        "total_bytes": 0,
        "freq": 0,
        "ranks": 0,
    }
    console = MyConsole(verbose=args.verbose)
    dominant_freq = np.nan
    t = np.array([])
    f_c = 1
    
    #! Sample the bandwidth evenly spaced in time
    tik = time.time()
    console.print("[cyan]Executing:[/] Discretization\n")
    # bandwidth = logicize(bandwidth)
    b_sampled, args.freq, [df_out[1], df_out[2]] = sample_data_and_prepare_plots(args, bandwidth, time_b, ranks
    )   
    console.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")

    tik = time.time()
    console.print(f"[cyan]Finding Scales:[/] \n")
    
    #! Continuous Wavelet transform
    # TODO: use DFT to select the scales (see tmp/test.py)
    # FIXME: determine how to specify the step of the scales
    
    # args.wavelet = "morl"
    # args.wavelet = "haar"
    # args.wavelet = 'cmor' #Phase is not rally needed, no need for complex
    # args.wavelet = 'mexh'
    # args.wavelet = 'morl'
    # args.wavelet = "cmor1.5-1.0"

    
    #NOTE: By making the signal alternate, the wavelet achieves better results
    # b_sampled = b_sampled - 400000
    method = "dft"
    # method = "scale"
    if "scale" in method:
        scales = get_scales(args,b_sampled)
    elif "dft" in method: #use dft
        args.n_freq = 5
        use_dominant_only = False
        scales = []
        t = time_b[0] + np.arange(0, len(b_sampled)) * 1/args.freq
        prediction, df_out, share = ftio_dft(args, b_sampled, t)  
        dominant_freq, _ = get_dominant_and_conf(prediction)

        # args.wavelet = "cmor0.01-1.0"
        b = 1/(dominant_freq)
        f_c = dominant_freq#/args.freq
        args.wavelet = f"cmor{b:f}-{f_c:f}"
        # args.wavelet = f"cmor{args.freq/dominant_freq}-{dominant_freq}"
        if not np.isnan(dominant_freq) and use_dominant_only:
        # Use only the dominant frequency
            scales = frequency2scale(args.wavelet, np.array([dominant_freq]))/args.freq
            # c = 1  # central frequency for wavelet (Mexican Hat = 1)
            # scales = np.array([c / dominant_freq])  # Scale corresponding to the frequency
        elif not use_dominant_only:
        # use the top frequencies
            top_freqs = prediction['top_freq']['freq'] if 'freq' in prediction['top_freq'] else []
            top_freqs = np.delete(top_freqs, np.where(top_freqs == 0))
            if len(top_freqs) > 0:
                if f_c == 1:
                    scales = frequency2scale(args.wavelet, np.array(top_freqs))
                else:
                    scales = f_c/np.array(top_freqs)
                console.print(f"Wavelet: {args.wavelet}")
                console.print(f"Scales: {scales}")
                console.print(f"Dominant freq: {dominant_freq}")
                console.print(f"Top freq: {top_freqs}")
            
        if len(scales) == 0:
            console.info("[red] No dominant freq found with DFT -> Falling back to default method [/]")
            scales = get_scales(args,b_sampled)

    tik = time.time()
    console.print(
        f"\n[cyan]Scales found:[/] {time.time() - tik:.3f} s")
    console.print(
        f"[cyan]Executing:[/] {args.transformation.upper()} + {args.outlier}\n"
    )

    # b_sampled = b_sampled - np.mean(b_sampled) #downshift by average
    coefficients, frequencies = wavelet_cont(b_sampled, args.wavelet, scales, args.freq)
    power_spectrum = np.abs(coefficients)**2  # Power of the wavelet transform
    
    # FIXME: Rather than averaging the power, find the dominant frequency by examining the power spectrum
    # NOTE: The power spectrum specifies how much a examined frequency is presented in a signal contributes to the signal
    # NOTE: Don't rely on the hight of the power spectrum to find the dominant frequency
    # Find the dominant scale by averaging the power across all time points
    average_power_per_scale = power_spectrum.mean(axis=1)
    dominant_scale_idx = np.argmax(average_power_per_scale)
    dominant_scale = scales[dominant_scale_idx]
    # Norm the power spectrum 
    # power_spectrum = power_spectrum/np.max(power_spectrum[dominant_scale_idx, :])
    
    # Extract the power at the dominant scale
    power_at_scale = power_spectrum[dominant_scale_idx, :]
    # Extract dominant frequency
    dominant_frequency = frequencies[dominant_scale_idx]
    console.print(f"dominant_scale: {dominant_scale:.3f}, dominant_frequency: {dominant_frequency:.3f}")

    # Find local peaks in the power spectrum (use a sliding window approach)
    peaks, _ = find_peaks(power_at_scale, height=0.5)  # 'distance' avoids detecting too close peaks
    if len(t) == 0:
        t = time_b[0] + np.arange(0, len(b_sampled)) * 1/args.freq
    peak_times = t[peaks]

    # plot functions
    if any(x in args.engine for x in ["mat", "plot"]):
        # plot_spectrum(args, t, power_at_scale, dominant_scale, peaks)
        # _ = plot_wave_cont(b_sampled, frequencies, args.freq, time_b, coefficients)
        fig = plot_wave_cont_and_spectrum(args, t, frequencies,power_spectrum, power_at_scale, dominant_scale, peaks)
        fig.show()
        fig = plot_scales(args, t, b_sampled, power_spectrum, frequencies, scales)
        fig.show()
        fig = plot_scales_all_in_one(args, t, b_sampled, power_spectrum/np.max(b_sampled), frequencies, scales)
        fig.show()
    
    # Calculate the period (time difference between consecutive peaks)
    if len(peak_times) > 1:
        periods = np.diff(peak_times)  # Differences between consecutive peak times (periods)
    else:
        periods = []
        
    dominant_index = []

    if any(x in args.engine for x in ["mat", "plot"]):
        df_out[0], df_out[3] = prepare_plot_wavelet_cont(
            frequencies, np.zeros(len(frequencies)), dominant_index, coefficients, b_sampled, ranks
        )

    console.print(
        f"\n[cyan]{args.transformation.upper()} + {args.outlier} finished:[/] {time.time() - tik:.3f} s"
    )
    return prediction, df_out , share


def prepare_plot_wavelet_cont(
    frequencies:np.ndarray,
    conf:np.ndarray,
    dominant_index:list[float],
    coefficients:np.ndarray,
    b_sampled:np.ndarray,
    ranks:int,
) ->  tuple[list[pd.DataFrame], list[pd.DataFrame]]:
    """
    Prepares data for plotting the Discrete Fourier Transform (DFT) by creating two DataFrames.

    Args:
        frequencies: An array of frequency values.
        conf: An array of confidence values corresponding to the frequencies.
        dominant_index: The index (or indices) of the dominant frequency component.
        amp: An array of amplitudes corresponding to the frequencies.
        phi: An array of phase values corresponding to the frequencies.
        b_sampled: An array of sampled bandwidth values.
        ranks: The number of ranks.

    Returns:
        tuple[list[pd.DataFrame], list[pd.DataFrame]]: A tuple containing two lists of DataFrames:
            - The first list contains a DataFrame with amplitude (A), phase (phi), sampled bandwidth (b_sampled), ranks, frequency (freq), 
            period (T), and confidence (conf) values.
            - The second list contains a DataFrame with the dominant frequency, its index (k), its confidence, and the ranks.
    """
    df0 = []
    df1 = []

    # Automatically handle multi-dimensional coefficients
    df_data = {
    **{f"coefficients_dim_{i+1}": value for i, value in enumerate(coefficients)},
    **{f"frequencies_dim_{i+1}": np.repeat(value,len(b_sampled)) for i, value in enumerate(frequencies)},
    "b_sampled": b_sampled,
    "ranks": np.repeat(ranks, len(b_sampled)), 
    "k": np.arange(0, len(b_sampled)),       
    }
    # Append the DataFrame
    df0.append(pd.DataFrame(df_data))

    df1.append(
        pd.DataFrame(
            {
                "dominant": frequencies[dominant_index],
                "k": dominant_index,
                "conf": conf[dominant_index],
                "ranks": np.repeat(ranks, len(dominant_index)),
            }
        )
    )
    return df0, df1

