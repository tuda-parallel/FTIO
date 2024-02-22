"""Module contating function functions to discretize the data.
"""

from __future__ import annotations
import numpy as np


def sample_data(b: np.ndarray, t: np.ndarray, freq=-1) -> tuple[np.ndarray, float, str]:
    """Discretize the data according to the frequency

    Args:
        b (array): bandwidth
        t (array): time
        freq (int, optional): sampling frequency. Defaults to -1, calculates the optimal sampling
        frequency inside this funciton

    Returns:
        _type_: b_sampled, sampling frequency (in case -1), and text 
        
    """
    text = ""
    text += f"Time window: {t[-1]-t[0]:.2f} s\n"
    text += f"Frequency step: {1/(t[-1]-t[0]) if (t[-1]-t[0]) != 0 else 0:.3e} Hz\n"

    # ? calculate recommended frequency:
    if len(t) == 0:
        return np.empty(0), 0, " "
    if freq == -1:
        t_rec = np.inf
        for i in range(0, len(t) - 1):
            if (
                t_rec > (t[i + 1] - t[i])
                and (t[i + 1] - t[i]) != 0
                and (t[i + 1] - t[i]) >= 0.001
            ):
                t_rec = t[i + 1] - t[i]
                # print("tre_c",t_rec, "t[i+1] ",t[i+1], "t[i]", t[i])
        freq = 2 / t_rec
        text += f"Recomended sampling frequency: {freq:.3e} Hz\n"
    else:
        text += f"Sampling frequency:  {freq:.3e} Hz\n"
    N = int(np.floor((t[-1] - t[0]) * freq))
    text += f"Expected samples: {N}\n"
    # print("    '-> \033[1;Start time: %f s \033[1;0m"%t[0])

    # ? sample the data with the recommended frequency
    # t_sampled = np.zeros(N) #t[0]+np.arange(N)*1/freq
    b_sampled = np.zeros(N)
    n = len(t)
    counter = 0
    n_old = 0
    t_step = t[0]
    # error   = 0
    # errorStep   = 0
    for _ in range(0, N):
        for i in range(n_old, n):
            if (t_step >= t[i]) and (t_step < t[i + 1]) or i == n - 1:
                n_old = i  # no need to itterate over entire array
                b_sampled[counter] = b[i]
                counter = counter + 1
                break
        t_step = t_step + 1 / freq

    #! Abstraction error
    v_a = np.sum(np.abs(b_sampled * np.repeat(1 / freq, len(b_sampled))))
    v_0 = np.sum(b * (np.concatenate([t[1:], t[-1:]]) - t))
    # E = (abs(error))/(V0) if V0 > 0 else 0
    error = (abs(v_a - v_0)) / v_0 if v_0 > 0 else 0
    text += f"Abstraction error: {error:.5f}\n"

    return b_sampled, freq, text[:-1]


def sample_data_same_size(b: np.ndarray, t:np.ndarray, freq=-1, n_bins=-1) -> tuple[np.ndarray,np.ndarray]:
    """Dsicretize the data according to the frequency and holds value

    Args:
        b (array): bandwidth
        t (array): time
        freq (int, optional): sampling frequency. Defaults to -1, calculates the optimal sampling
        frequency inside this funciton
        n_bins (int,optinal): number of desired bins

    Returns:
        _type_: b_sampled and sampling frequency (in case -1)
    """
    print(f"    '-> \033[1;34mBins: {n_bins}  \033[1;0m")
    b_sampled = np.zeros(n_bins)
    n_old = 0
    counter = 0
    t_step = 0
    n = len(b)
    for k in range(0, n_bins):
        if (t_step < t[0]) or (t_step > t[-1]):
            counter = counter + 1
        else:
            for i in range(n_old, n):
                if (t_step >= t[i]) and (t_step < t[i + 1]) or i == n - 1:
                    n_old = i  # no need to itterate over entire array
                    b_sampled[counter] = b[i]
                    counter = counter + 1
                    break
        t_step = t_step + 1 / freq

    t = np.arange(0, n_bins) * 1 / freq
    return b_sampled, t
