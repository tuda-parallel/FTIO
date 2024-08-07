import pandas as pd 
import numpy as np


def extract_data(data):
    """Extracts relevant data that is not NaN 

    Args:
        data (_type_): _description_

    Returns:
        _type_: _description_
    """
    # Prepare the data for the plot
    data_points = []

    for d in data:
        if len(d['dominant_freq']) > 0 and len(d['conf']) > 0:
            max_conf_index = np.argmax(d['conf'])
            dominant_freq = d['dominant_freq'][max_conf_index]
            conf = d['conf'][max_conf_index]*100
            phi = d['phi'][max_conf_index]
            amp = d['amp'][max_conf_index]
            t_s = d['t_start']
            t_e = d['t_end']
            data_points.append((d['metric'], dominant_freq, conf, amp, phi, t_s, t_e))
        else:
            continue 
            data_points.append((d['metric'], np.NaN, np.NaN, np. NaN, np.NaN, np. NaN))

    # Create a DataFrame for the plot
    df = pd.DataFrame(data_points, columns=['Metric', 'Dominant Frequency', 'Confidence', 'Amp', 'Phi', 'time start', 'time end'])
    df.sort_values(by='Dominant Frequency',inplace=True)

    return df
