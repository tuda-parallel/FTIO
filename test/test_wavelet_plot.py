"""
Functions for testing the ioplot functionality of the ftio package.
"""

import os
import numpy as np
from ftio.freq._wavelet import wavelet_cont
from ftio.parse.extract import extract_fields, get_time_behavior_and_args
from ftio.plot.plot_wavelet import plot_scales

def test_plot_wavelet():
    """Test the core functionality of ftio with frequency option."""
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/ior/collective/1536_new.json")
    args = ["ftio", file, "-e", "no", "-c", "-tr", "wave_cont"]
    data, args = get_time_behavior_and_args(args) 
    b_sampled,time_b, _, _ = extract_fields(data)
    scales =  np.arange(1, 10)
    sampling_frequency = 10
    coefficients, frequencies = wavelet_cont(b_sampled, args.wavelet, scales, sampling_frequency)
    power_spectrum = np.abs(coefficients)**2  # Power of the wavelet
    t = time_b[0] + np.arange(0, len(b_sampled)) * 1/sampling_frequency
    _ = plot_scales(args, t, b_sampled, power_spectrum, frequencies, scales)
    assert True
