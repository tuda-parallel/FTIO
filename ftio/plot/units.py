import numpy as np
import pandas as pd

def set_unit(arr:np.ndarray) -> tuple[str, float]:
    """set unit for the plots

    Args:
        arr (np.ndarray): array

    Returns:
        unit (string): unit in GB/s, MB/s, KB/s or B/s
        arr: scaled array according to the unit
    """
    unit = "B/s"
    order = 1e-0
    if isinstance(arr, np.ndarray):
        pass
    elif isinstance(arr, pd.DataFrame):
        arr = arr.to_numpy()
    
    if arr.size > 0:
        order = np.log10(np.max(arr))

    if order > 9:
        order = 1e-9
        unit = "GB/s"
    elif order > 6:
        order = 1e-6
        unit = "MB/s"
    elif order > 3:
        order = 1e-3
        unit = "KB/s"
    else:
        pass

    return unit, order



def find_unit(df_t,index,index2,index_ind,index2_ind,args):
    unit = "B/s"
    order = 1e-0
    if args.avr:
        tmp_unit, tmp_order = set_unit(df_t[1]["b_overlap_avr"][index][index2])
        if tmp_order < order:
            order = tmp_order
            unit = tmp_unit

    if args.sum:
        tmp_unit, tmp_order = set_unit(df_t[1]["b_overlap_sum"][index][index2])
        if tmp_order < order:
            order = tmp_order
            unit = tmp_unit

    if args.ind:
        tmp_unit, tmp_order = set_unit(df_t[3]["b_overlap_ind"][index_ind][index2_ind])
        if tmp_order < order:
            order = tmp_order
            unit = tmp_unit

    return unit, order