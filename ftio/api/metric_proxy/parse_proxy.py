import sys
import numpy as np
import json
from time import process_time
from ftio.freq.helper import MyConsole
from ftio.api.metric_proxy.req import MetricProxy



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
                x = np.nan_to_num(x=x, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
                t_out = x[:,0]
                b_out = x[:,1]
                #remove None from b
                b_out[b_out==None]= 0
                #reduce to derivative
                if "deriv" not in key:
                    if verbose:
                        print("removing aggregation")
                    b_shifted = b_out[:-1]
                    b_shifted = np.insert(b_shifted,0,0)
                    b_out =  b_out - b_shifted
                    break
    return b_out,t_out


def filter_deriv(json_data,deriv_and_not_deriv:bool=True, exclude=None):
    out = {}
    t = process_time()
    metrics = json_data['metrics'].keys()
    # extract either derive or all but not all
    if not deriv_and_not_deriv:
        metrics = clean_metrics(metrics)
        
    if exclude:
        for metric in metrics:
            if all(n not in metric for n in exclude):
                b_out,t_out = extract(json_data,metric, False)
                out[metric]=[b_out,t_out]
        text=', '.join([str(item) for item in exclude])
        CONSOLE.info(f"[green]Excluded matches for: \\[{text}]\nMetrics reduced further from {len(metrics)} to {len(out)}[/]")
    else:
        for metric in metrics:
            b_out,t_out = extract(json_data,metric, False)
            out[metric]=[b_out,t_out]
    
    elapsed_time = process_time() - t
    CONSOLE.info(f"\n[green]Parsing time: {elapsed_time} s[/]")
    
    return out


def parse_all(file_path:str,deriv_and_not_deriv:bool=True, exclude=None)-> dict:
    """parses all metrics from proxy

    Args:
        file_path (str): pass to proxy JSON file
        deriv_and_not_deriv (bool, optional): Removes the metrics in case a similar metrics, which start with deriv is presented. Defaults to True.
        exclude (list,optional): list of metrics to exclude

    Returns:
        dict: parsed metrics with 2D numpy array
    """
    try:
        with open(file_path, 'r') as json_file:
            json_data = json.load(json_file)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Unable to decode JSON from file '{file_path}'. Check if the file is valid JSON.")
        return {}

    return filter_deriv(json_data,deriv_and_not_deriv,exclude)


def load_proxy_trace_stdin(deriv_and_not_deriv:bool=True, exclude=None):
    try:
    # Read JSON from stdin
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
    else:
        return filter_deriv(data,deriv_and_not_deriv,exclude)


def clean_metrics(metrics):
    deriv_metrics =  [metric for metric in metrics if metric.startswith("deriv")]
    non_deriv_metrics = [metric for metric in metrics if not metric.startswith("deriv")]
    cleaned_metrics = [metric for metric in metrics if not (metric in non_deriv_metrics and "deriv__" + metric in deriv_metrics)]
    CONSOLE.info(f"[green]Metrics reduced from {len(metrics)} to {len(cleaned_metrics)}[/]")
    return cleaned_metrics



def get_all_metrics(job_id):
    mp = MetricProxy()
    metrics = {}
    all_metrics= mp.metric(job_id)
    for metric in all_metrics:
        value = mp.trace_metric(job_id,metric)
        t_out = np.array([item[0] for item in value])
        b_out = np.array([item[1] for item in value])
        # derive b
        b_out = numerical_derivative(t_out,b_out)
        metrics[metric]=[b_out,t_out]
        
    return metrics

# Calculate the numerical derivative using central differences
def numerical_derivative(t, f):
    n = len(t)
    df_dt = np.zeros(n)
    if n > 10:
        # Forward difference for the first point
        df_dt[0] = (f[1] - f[0]) / (t[1] - t[0])

        # Central differences for the interior points
        for i in range(1, n - 1):
            df_dt[i] = (f[i + 1] - f[i - 1]) / (t[i + 1] - t[i - 1])

        # Backward difference for the last point
        df_dt[-1] = (f[-1] - f[-2]) / (t[-1] - t[-2])  
    return df_dt
