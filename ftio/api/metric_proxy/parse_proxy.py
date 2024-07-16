import numpy as np
import json


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


def extract(json_data, match, silent=False):
    b_out = np.array([])
    t_out  = np.array([])
    for key, value in json_data.items():
        if isinstance(value, dict):
            b_out,t_out = extract(value, match)
            if len(b_out) > 0:
                break
        else:
            if match == key:
                if not silent:
                    print(f"matched {key}")
                x = np.array(value)
                t_out = x[:,0]
                b_out = x[:,1]
                #reduce to derivative
                if "deriv" not in key:
                    if not silent:
                        print("removing aggregation")
                    b_shifted = b_out[:-1]
                    b_shifted = np.insert(b_shifted,0,0)
                    b_out =  b_out - b_shifted
                    break
    return b_out,t_out


def parse_all(file_path)-> dict:
    out = {}
    try:
        with open(file_path, 'r') as json_file:
            json_data = json.load(json_file)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return out
    except json.JSONDecodeError:
        print(f"Error: Unable to decode JSON from file '{file_path}'. Check if the file is valid JSON.")
        return out

    for metric in json_data['metrics'].keys():
        b_out,t_out = extract(json_data,metric, True)
        out[metric]=[b_out,t_out]

    return out