"""
TODO:
binary image:
- denoise signal (preprocessing?)
- #peaks per window (outlier, bursts)
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
    #Zxx = Zxx.transpose()

    bin_im = np.zeros_like(Zxx)

    rows = np.shape(Zxx)[0]
    N = np.shape(Zxx)[1]
    for i in range(0,rows):
        # TODO: does this make sense?
        freqs = np.abs(Zxx[i,0:N//2])

        peaks = find_peaks(freqs)

        prom = peak_prominences(freqs, peaks[0])[0]

        if(prom.size > 0):
            # TODO: number of peaks per window
            ind = np.argmax(prom)
            bin_im[i][ind] = 1

    return bin_im