import numpy as np
import pandas as pd

def set_unit(arr:np.ndarray, suffix = "B/s") -> tuple[str, float]:
    """set unit for the plots

    Args:
        arr (np.ndarray | float): array or float
        unit (optional): default B/s

    Returns:
        unit (string): unit in GB/s, MB/s, KB/s or B/s
        arr: scaled array according to the unit
    """
    unit = suffix
    order = 1e-0
    if isinstance(arr, np.ndarray):
        pass
    elif isinstance(arr, pd.DataFrame):
        arr = arr.to_numpy()
    elif isinstance(arr,float) or isinstance(arr,int):
        arr = np.array(arr)
    
    if arr.size > 0 and np.max(arr) > 0:
        order = np.log10(np.max(arr))

    if order > 9:
        order = 1e-9
        unit = "G"+suffix
    elif order > 6:
        order = 1e-6
        unit = "M"+suffix
    elif order > 3:
        order = 1e-3
        unit = "K"+suffix
    else:
        order = 1 # in case order is negative 
        unit = suffix

    return unit, order



def find_unit(df_t,index,index2,index_ind,index2_ind,args, offset=1):
    """
    Determines the appropriate unit and order of magnitude for data values 
    based on the provided arguments and data structure.

    Args:
        df_t (list): A list of dataframes or similar structures containing 
                        the data to analyze.
        index (int): The primary index for accessing data in the first dataframe.
        index2 (int): The secondary index for accessing data in the first dataframe.
        index_ind (int): The primary index for accessing data in the third dataframe.
        index2_ind (int): The secondary index for accessing data in the third dataframe.
        args (Namespace): An object containing boolean attributes (`avr`, `sum`, `ind`) 
                            that determine which data fields to evaluate.
        offset (float, optional): A multiplier applied to the data values before 
                                    determining the unit. Defaults to 1.

    Returns:
        tuple: A tuple containing:
            - unit (str): The selected unit of measurement (e.g., "B/s").
            - order (float): The corresponding order of magnitude for the unit.
    """
    unit = "B/s"
    order = 1e-0
    if args.avr and "b_overlap_avr" in df_t[1]:
        tmp_unit, tmp_order = set_unit(df_t[1]["b_overlap_avr"][index][index2]*offset)
        if tmp_order < order:
            order = tmp_order
            unit = tmp_unit

    if args.sum and "b_overlap_sum" in df_t[1]:
        tmp_unit, tmp_order = set_unit(df_t[1]["b_overlap_sum"][index][index2]*offset)
        if tmp_order < order:
            order = tmp_order
            unit = tmp_unit

    if args.ind  and "b_overlap_ind" in df_t[3]:
        tmp_unit, tmp_order = set_unit(df_t[3]["b_overlap_ind"][index_ind][index2_ind]*offset)
        if tmp_order < order:
            order = tmp_order
            unit = tmp_unit

    return unit, order