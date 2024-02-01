""" Extracts time behavior form parsed data

"""
import pandas as pd 


def get_time_behavior(df) -> list[dict]:
    """Get the time behavior

    Args:
        df (dataframe): obtained from scales.py
    """
    out = []
    files = [int(i) for i in pd.unique(df[0]["number_of_ranks"])]
    for i in files:
        ranks = df[1]["number_of_ranks"].isin([i])
        if len(df[1]["file_index"][ranks]) != 0:
            for j in range(0, int(df[1]["file_index"][ranks].max() + 1)):
                # print(f"  \033[1;32mRanks {i}\033[1;0m")
                file_index = df[1]["file_index"][ranks].isin([j])
                time = df[1]["t_overlap"][ranks][file_index].to_numpy()
                bandwidth = df[1]["b_overlap_avr"][ranks][file_index].to_numpy()
                try:
                    total_bytes = df[0]["total_bytes"].to_numpy()
                    total_bytes = int(float(total_bytes[-1]))
                except ValueError:
                    total_bytes = 0
                    # expe.center()np.sum(bandwidth * (np.concatenate([time[1:], time[-1:]]) - time)
                tmp = {
                    "time": time,
                    "bandwidth": bandwidth,
                    "total_bytes": total_bytes,
                    "ranks": i
                    }
                out.append(tmp)
    return out
