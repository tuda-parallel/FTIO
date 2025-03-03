"""
TODO:
- window function CM?
- find an CM implementation to verify approach
- adapt min_win to f_s
"""

import numpy as np
from scipy.fft import fft
from scipy.fftpack import fftshift

"""
Pei, S. C., & Huang, S. G. (2012).
STFT with adaptive window width based on the chirp rate.
IEEE Transactions on Signal Processing, 60(8), 4065-4080.
"""

min_win = 80
max_win = 500

alpha = 0.1
beta = 5
p = 4
L = 105

# don't know
# https://de.mathworks.com/matlabcentral/answers/356692-how-to-normalize-a-fft-to-plot-in-frequency-domain
def normalize_fft(yf):
    yf_norm = fftshift(yf/ len(yf))
    return yf_norm

def cm3(x):
    win_len = min_win

    max_win = len(x)
    p = int(len(x) * 0.005)
    L = (max_win - min_win) // p

    sum = np.zeros((L,), dtype=np.complex128)

    for j in range(0,L):
        # zeropad
        rem = len(x) % win_len
        if (rem != 0):
            x_padded = np.pad(x, (0, win_len-rem), 'constant')
        else:
            x_padded = x

        # nd array korrekte dim
        rows = int(len(x_padded)/win_len) * 2 -1
        output = np.empty(shape=(rows, win_len), dtype=np.complex128)

        overlap = win_len//2
        for i in range(0, rows):
            windowed = x[overlap*i:overlap*i+win_len]
            yf = fft(windowed)
            yf_norm = normalize_fft(yf) ** alpha
            sum[j] = sum[j] + np.sum(yf_norm)

        sum[j] = 1 / sum[j]
        win_len = win_len + p

    peak = np.argmax(sum)
    final_win_len = min_win + p*peak

    print(final_win_len)
    return final_win_len

def cm4(x):
    win_len = min_win

    max_win = len(x)
    p = int(len(x) * 0.005)
    L = (max_win - min_win) // p

    sum = np.zeros((L,), dtype=np.complex128)

    for j in range(0,L):
        # zeropad
        rem = len(x) % win_len
        if (rem != 0):
            x_padded = np.pad(x, (0, win_len-rem), 'constant')
        else:
            x_padded = x

        # nd array korrekte dim
        rows = int(len(x_padded)/win_len) * 2 -1
        output = np.empty(shape=(rows, win_len), dtype=np.complex128)

        overlap = win_len//2
        for i in range(0, rows):
            windowed = x[overlap*i:overlap*i+win_len]
            yf = fft(windowed)
            yf_norm = normalize_fft(yf) ** beta
            sum[j] = sum[j] + np.sum(yf_norm)

        win_len = win_len + p

    peak = np.argmax(sum)
    final_win_len = min_win + p*peak

    print(final_win_len)

    return final_win_len

def cm5(x):
    win_len = min_win

    max_win = len(x)
    p = int(len(x) * 0.005)
    L = (max_win - min_win) // p

    sum = np.zeros((L,), dtype=np.complex128)

    for j in range(0,L):
        # zeropad
        rem = len(x) % win_len
        if (rem != 0):
            x_padded = np.pad(x, (0, win_len-rem), 'constant')
        else:
            x_padded = x

        # nd array korrekte dim
        rows = int(len(x_padded)/win_len) * 2 -1
        output = np.empty(shape=(rows, win_len), dtype=np.complex128)

        sum1 = 0
        sum2 = 0

        overlap = win_len//2
        for i in range(0, rows):
            windowed = x[overlap*i:overlap*i+win_len]
            yf = fft(windowed)
            yf_norm = normalize_fft(yf)
            sum1 = sum1 + np.sum(yf_norm) ** beta
            sum2 = sum2 + np.sum(yf_norm) ** alpha

        sum[j] = (sum1 ** (1/beta)) / (sum2 ** (1/alpha))
        win_len = win_len + p

    peak = np.argmax(sum)
    final_win_len = min_win + p*peak

    print(final_win_len)
    return final_win_len