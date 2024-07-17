import numpy as np
import json
from time import process_time
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()
CONSOLE.set(True)

def parse(file_path, match="proxy_component_critical_temperature_celcius")-> tuple[np.ndarray,np.ndarray]:
    b_out = np.array([])
    t_out = np.array([])
    try:
        with open(file_path, 'r') as json_file:
            json_data = json.load(json_file)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return b_out,t_out
    except json.JSONDecodeError:
        print(f"Error: Unable to decode JSON from file '{file_path}'. Check if the file is valid JSON.")
        return b_out,t_out

    b_out,t_out = extract(json_data, match)

    if len(b_out) == 0:
        print("No match found. Exciting\n")
        exit(0)
    return b_out,t_out


def extract(json_data, match, verbose=False):
    b_out = np.array([])
    t_out  = np.array([])
    for key, value in json_data.items():
        if isinstance(value, dict):
            b_out,t_out = extract(value, match, verbose)
            if len(b_out) > 0:
                break
        else:
            if match == key:
                if verbose:
                    print(f"matched {key}")
                x = np.array(value)
                t_out = x[:,0]
                b_out = x[:,1]
                #reduce to derivative
                if "deriv" not in key:
                    if verbose:
                        print("removing aggregation")
                    b_shifted = b_out[:-1]
                    b_shifted = np.insert(b_shifted,0,0)
                    b_out =  b_out - b_shifted
                    break
    return b_out,t_out


def parse_all(file_path:str,deriv_and_not_deriv:bool=True)-> dict:
    """parses all metrics from proxy

    Args:
        file_path (str): pass to proxy JSON file
        deriv_and_not_deriv (bool, optional): Removes the metrics in case a similar metrics, which start with deriv is presented. Defaults to True.

    Returns:
        dict: parsed metrics with 2D numpy array
    """
    out = {}
    t = process_time()
    try:
        with open(file_path, 'r') as json_file:
            json_data = json.load(json_file)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return out
    except json.JSONDecodeError:
        print(f"Error: Unable to decode JSON from file '{file_path}'. Check if the file is valid JSON.")
        return out

    metrics = json_data['metrics'].keys()
    # extract either derive or all but not all
    if not deriv_and_not_deriv:
        metrics = clean_metrics(metrics)
        elapsed_time = process_time() - t

    for metric in metrics:
        b_out,t_out = extract(json_data,metric, False)
        out[metric]=[b_out,t_out]

    CONSOLE.info(f"\n[green]Parsing time: {elapsed_time} s[/]")
    return out


def clean_metrics(metrics):
    deriv_metrics =  [metric for metric in metrics if metric.startswith("deriv")]
    non_deriv_metrics = [metric for metric in metrics if not metric.startswith("deriv")]
    cleaned_metrics = [metric for metric in metrics if not (metric in non_deriv_metrics and "deriv__" + metric in deriv_metrics)]
    CONSOLE.info(f"[green]Metrics reduced from {len(metrics)} to {len(cleaned_metrics)}[/]")
    return cleaned_metrics

