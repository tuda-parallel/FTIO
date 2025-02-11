"""
TODO:
binary image:
- denoise signal (preprocessing?)
- adjust prominence threshold
"""

import numpy as np
from scipy.signal import find_peaks, peak_prominences

"""
Rankine, L., Mesbah, M., & Boashash, B. (2007).
IF estimation for multicomponent signals using image processing
techniques in the time-frequency domain.
Signal Processing, 87(6), 1234-1250.
"""
def binary_image(Zxx):
    bin_im = np.zeros_like(Zxx, dtype="uint8")
    rows = np.shape(Zxx)[0]

    for i in range(0,rows):
        freqs = np.abs(Zxx[i])
        peaks = find_peaks(freqs)
        prom = peak_prominences(freqs, peaks[0])[0]

        if(prom.size > 0):
            for ind in range(0,len(prom)):
                if prom[ind] > 0.01:
                    _ind = peaks[0][ind]
                    bin_im[i][_ind] = 255

    return bin_im