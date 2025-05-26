import json
import re
import sys
from time import process_time

import numpy as np

from ftio.api.metric_proxy.req import MetricProxy
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()
CONSOLE.set(True)


def parse(
    file_path, match="proxy_component_critical_temperature_celcius"
) -> tuple[np.ndarray, np.ndarray]:
    b_out = np.array([])
    t_out = np.array([])
    try:
        with open(file_path, "r") as json_file:
            json_data = json.load(json_file)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return b_out, t_out
    except json.JSONDecodeError:
        print(
            f"Error: Unable to decode JSON from file '{file_path}'. Check if the file is valid JSON."
        )
        return b_out, t_out

    b_out, t_out = extract(json_data, match)

    if len(b_out) == 0:
        print("No match found. Exciting\n")
        exit(0)
    return b_out, t_out


def extract(json_data, match, verbose=False):
    b_out = np.array([])
    t_out = np.array([])
    for key, value in json_data.items():
        if isinstance(value, dict):
            b_out, t_out = extract(value, match, verbose)
            if len(b_out) > 0:
                break
        else:
            if match == key:
                if verbose:
                    print(f"matched {key}")
                x = np.array(value)
                x = np.nan_to_num(
                    x=x, copy=False, nan=0.0, posinf=0.0, neginf=0.0
                )
                t_out = x[:, 0]
                b_out = x[:, 1]
                # remove None from b
                b_out[b_out == None] = 0
                # reduce to derivative
                if "deriv" not in key:
                    if verbose:
                        print("removing aggregation")
                    b_shifted = b_out[:-1]
                    b_shifted = np.insert(b_shifted, 0, 0)
                    b_out = b_out - b_shifted
                    break
    return b_out, t_out


def filter_metrics(
    json_data,
    filter_deriv: bool = True,
    exclude=None,
    scale_t: float = 1,
    rename: dict = {},
):
    out = {}
    t = process_time()
    metrics = json_data["metrics"].keys()
    # extract either derive or all
    if filter_deriv:
        metrics = clean_metrics(metrics)

    if exclude:
        old_length = len(metrics)
        metrics = [
            metric
            for metric in metrics
            if all(n not in metric for n in exclude)
        ]
        text = ", ".join([str(item) for item in exclude])
        CONSOLE.info(
            f"[blue]\nExcluded matches for: \\[{text}]\nMetrics reduced further from {old_length} to {len(metrics)}[/]"
        )

    for metric in metrics:
        b_out, t_out = extract(json_data, metric, False)
        out[metric] = [b_out, t_out * scale_t]

    # rename keys if only one metric passed
    if exclude:
        if "func" not in exclude:
            keys_to_rename = []
            for metric in out:
                if "func" in metric:
                    keys_to_rename.append(
                        (
                            metric,
                            "f_" + re.findall(r"func__(.*?)__", metric)[0],
                        )
                    )
            for old_key, new_key in keys_to_rename:
                original_new_key = new_key
                suffix = 1
                while new_key in out:
                    new_key = f"{original_new_key}_{suffix}"
                    suffix += 1
                out[new_key] = out.pop(old_key)

        if len(set(["time", "hits", "size"]) & set(exclude)) == 2:
            keys_to_rename = [
                (metric, metric.rsplit("__", 1)[-1]) for metric in out
            ]
            # Perform renaming after collecting all keys
            if keys_to_rename:
                CONSOLE.info(
                    f"[blue]\nRenaming Metrics: Removing [{keys_to_rename[-1][-1]}] from names[/]"
                )

            for old_key, new_key in keys_to_rename:
                out[new_key] = out.pop(old_key)

    elapsed_time = process_time() - t
    CONSOLE.info(f"[blue]Parsing time: {elapsed_time} s[/]")

    return out


def parse_all(
    file_path: str, filter_deriv: bool = True, exclude=None, scale_t: float = 1
) -> dict:
    """parses all metrics from proxy

    Args:
        file_path (str): pass to proxy JSON file
        filter_deriv (bool, optional): Removes the metrics in case a similar metrics, which start with deriv is presented. Defaults to True.
        exclude (list,optional): list of metrics to exclude
        scale_t (float, optional): scale time unit (default 1). Default unit is "s"

    Returns:
        dict: parsed metrics with 2D numpy array
    """
    CONSOLE.info(f"\n[blue]Current file: {file_path}[/]")
    if scale_t != 1:
        CONSOLE.info(f"\n[yellow]Scaling time by: {scale_t}[/]")
    try:
        with open(file_path, "r") as json_file:
            json_data = json.load(json_file)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return {}
    except json.JSONDecodeError:
        print(
            f"Error: Unable to decode JSON from file '{file_path}'. Check if the file is valid JSON."
        )
        return {}

    return filter_metrics(json_data, filter_deriv, exclude, scale_t)


def load_proxy_trace_stdin(deriv_and_not_deriv: bool = True, exclude=None):
    try:
        # Read JSON from stdin
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
    else:
        return filter_metrics(data, deriv_and_not_deriv, exclude)


def clean_metrics(metrics: str):
    deriv_metrics = [
        metric for metric in metrics if metric.startswith("deriv")
    ]
    non_deriv_metrics = [
        metric for metric in metrics if not metric.startswith("deriv")
    ]
    cleaned_metrics = [
        metric
        for metric in metrics
        if not (
            metric in non_deriv_metrics and "deriv__" + metric in deriv_metrics
        )
    ]
    CONSOLE.info(
        f"[blue]Metrics reduced from {len(metrics)} to {len(cleaned_metrics)}[/]"
    )
    return cleaned_metrics


def get_all_metrics(job_id):
    mp = MetricProxy()
    metrics = {}
    all_metrics = mp.metric(job_id)
    for metric in all_metrics:
        value = mp.trace_metric(job_id, metric)
        t_out = np.array([item[0] for item in value])
        b_out = np.array([item[1] for item in value])
        # derive b
        b_out = numerical_derivative(t_out, b_out)
        metrics[metric] = [b_out, t_out]

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
