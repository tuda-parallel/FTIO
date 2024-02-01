"""Groups predicitions according to frequency step
"""

from __future__ import annotations
import numpy as np
from sklearn.cluster import DBSCAN
from ftio.prediction.helper import get_dominant

def group_step(data: list[dict]) -> tuple[list[dict], int]:
    """generates dict contaiting predictions. Aditionally the entries are grouped according to the frequency resolution between the predicitions.

    Args:
        data (dict): predicitions

    Returns:
        out (dict): data appended with a group field
        counter (int): Maximal number of groups
    """
    freq_new = 0
    freq_old = 0
    old_window = 0
    time_window = 0
    counter = 0
    out = []

    
    # Method 1: compare frequencies to their next neighbors
    for prediction in data:
        time_window = prediction["t_end"] - prediction["t_start"]
        if len(prediction["dominant_freq"]) >= 1:
            freq_new = prediction["dominant_freq"][0]
            if freq_old != 0 and old_window != 0:
                if abs(freq_old - freq_new) <= 2 * abs(
                    1 / time_window - 1 / old_window
                ):  # Same Frequency!
                    pass
                else:  # Different Frequency!
                    counter += 1
                out.append({**prediction, "group": counter})
            freq_old = freq_new
            old_window = time_window

    return out, counter


def group_dbscan(data: list[dict]) -> tuple[list[dict], int]:
    """generates dict contaiting predictions. Aditionally the entries are grouped according to dbscan with the frequency resolution as the eps distance.

    Args:
        data (dict): predicitions

    Returns:
        out (dict): data appended with a group field
        counter (int): Maximal number of groups
    """
    freq = []
    window = []
    tol_max = 0
    tol_min = np.inf
    old_window = 0
    time_window = 0
    counter = 0
    out = []

    for prediction in data:
        time_window = prediction["t_end"] - prediction["t_start"]
        if len(prediction["dominant_freq"]) >= 1:
            res = 1 / time_window - 1 / old_window if old_window != 0 else 0
            tol_max = max(abs(res), tol_max)
            # tol_min = min(abs(res), tol_min)
            freq.append(get_dominant(prediction))
            window.append(time_window)
            out.append(prediction)
            old_window = time_window
    
    tol_min = 1/np.std(window) if np.std(window) != 0 else 1e-8
    tol = 2*tol_max if tol_max < 3*tol_min else np.abs(1-(tol_min/np.mean(window)))*tol_max#3 times std means 99 points
    tol = tol if tol > 0 and tol != np.inf else 1e-8 #dbscan expects tol > 0
    # print(f"tol_min is: {tol_min}\ntol_max is: {tol_max}\ntol is: {tol}")

    if out:
        if len(out) == 1:
            counter = 0
            out[0]["group"] = counter
        else:
            X = np.column_stack((freq, freq))
            model = DBSCAN(eps=tol, min_samples=2).fit(X)
            counter = max(model.labels_)
            # print(f"X is {X}\n model.labels_ is {model.labels_}\nout is {out}")
            # for i,f in enumerate(freq):
            #     print(f"freq {f}\nmodel.labels_ is {model.labels_[i]}\ntol is {tol}")
            for i in range(0, len(out)):
                out[i]["group"] = model.labels_[i]

    return out, counter

