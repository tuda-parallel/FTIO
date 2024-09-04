""" Function for DTW calcluations
"""
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
import numpy as np
from threading import Thread



##Fill DTW Matrix
def fill_dtw_cost_matrix(s1, s2):
    l_s_1, l_s_2 = len(s1), len(s2)
    cost_matrix = np.zeros((l_s_1 + 1, l_s_2 + 1))
    for i in range(l_s_1 + 1):
        for j in range(l_s_2 + 1):
            cost_matrix[i, j] = np.inf
    cost_matrix[0, 0] = 0

    for i in range(1, l_s_1 + 1):
        for j in range(1, l_s_2 + 1):
            cost = abs(s1[i - 1] - s2[j - 1])
            # take last min from the window
            prev_min = np.min(
                [
                    cost_matrix[i - 1, j],
                    cost_matrix[i, j - 1],
                    cost_matrix[i - 1, j - 1],
                ]
            )
            cost_matrix[i, j] = cost + prev_min

    return cost_matrix[-1, -1]


##Call DTW function


def fdtw(s1, s2):
    distance, path = fastdtw(s1, s2, dist=euclidean)
    return distance, path



def evaluate_dtw(discret_arr, original_discret_signal, freq):
    dtw_k1, _ = fastdtw(discret_arr, original_discret_signal, dist=euclidean)
    print("    '-> \033[1;32mfreq %.2f Hz\033[1;0m --> dtw: %d" % (freq, dtw_k1))



def threaded_dtw(
    sum_all_components, df, dominant_X1, dominant_k1, dominant_X2, dominant_k2
):
    threads = []
    print("    '-> \033[1;35mCalculating DTW\033[1;0m")
    threads.append(
        Thread(
            target=evaluate_dtw,
            args=(
                dominant_X1,
                sum_all_components,
                df.iloc[dominant_k1]["freq"],
            ),
        )
    )
    threads.append(
        Thread(
            target=evaluate_dtw,
            args=(
                dominant_X2,
                sum_all_components,
                df.iloc[dominant_k2]["freq"],
            ),
        )
    )
    # t.append(Thread(target=evaluate_dtw, args=(dominant_X3,sum,df.iloc[dominant_k3]['freq'])))
    for thread in threads:
        thread.start()

    return threads
