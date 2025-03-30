import numpy as np
import importlib.util
from scipy.spatial.distance import euclidean
from threading import Thread

# Check if fastdtw is available
FASTDTW_AVAILABLE = importlib.util.find_spec("fastdtw") is not None
if FASTDTW_AVAILABLE:
    from fastdtw import fastdtw


## Fill DTW Cost Matrix using NumPy
def fill_dtw_cost_matrix(s1, s2):
    l_s_1, l_s_2 = len(s1), len(s2)
    # Initialize the cost matrix
    cost_matrix = np.full((l_s_1 + 1, l_s_2 + 1), np.inf)
    cost_matrix[0, 0] = 0  # Starting point

    # Fill the cost matrix
    for i in range(1, l_s_1 + 1):
        for j in range(1, l_s_2 + 1):
            cost = abs(s1[i - 1] - s2[j - 1])  # Euclidean distance
            # Take the minimum of three previous entries (top, left, diagonal)
            cost_matrix[i, j] = cost + min(
                cost_matrix[i - 1, j],  # from top
                cost_matrix[i, j - 1],  # from left
                cost_matrix[i - 1, j - 1],  # diagonal
            )

    return cost_matrix[-1, -1], None


## Call DTW function
def fdtw(s1, s2):
    if FASTDTW_AVAILABLE:
        return fastdtw(s1.reshape(-1, 1), s2.reshape(-1, 1), dist=euclidean)
    else:
        return fill_dtw_cost_matrix(s1, s2)


def evaluate_dtw(discret_arr, original_discret_signal, freq):
    # Call the fdtw function which handles both fastdtw and fallback
    dtw_k1, _ = fdtw(discret_arr, original_discret_signal)
    print(f"    '-> \033[1;32mfreq {freq:.2f} Hz\033[1;0m --> dtw: {dtw_k1}")


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

    for thread in threads:
        thread.start()

    return threads
