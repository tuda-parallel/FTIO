import sys
import os 
from datetime import datetime
import numpy as np
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.plot.freq_plot import convert_and_plot
from ftio.parse.csv_reader import read_csv_file
from ftio.api.trace_analysis.helper import quick_plot
from rich.console import Console
console = Console()

def main( argv=sys.argv[1:],verbose=True):

    full_path = get_path(argv,verbose)
    arrays = read_csv_file(full_path)
    b_r = np.array([])
    b_w = np.array([])
    b_b = np.array([])

    # for key, array in arrays.items():
    #     print(f"{key}: {array}")
    
    ranks = 10
    if 'read' in arrays:
        b_r = np.array(arrays['read']).astype(float)
    if 'write' in arrays:
        b_w = np.array(arrays['write']).astype(float)
    if 'both' in arrays:
        b_b = np.array(arrays['both']).astype(float)

    if 'timestamp' in arrays:
        entries = [datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f') for ts in arrays['timestamp']]
        t_s = entries[0]
        time_diffs_in_seconds = [(dt - t_s).total_seconds() for dt in entries]
        t = np.array(time_diffs_in_seconds)
    else:
        t_step =np.nan
        if '--time-step' not in argv:
            t_step = 1
            if verbose:
                console.print(f"[bold]Sampling rate set to {t_step}[/]")
        else:
            flag_index = argv.index('--time-step')
            t_step = float(argv[flag_index + 1])
            argv[flag_index:flag_index+2] = []
            if verbose:
                console.print(f"[bold green]Sampling rate set to {t_step} sec[/]")

        t = np.arange(0,len(b_w)*t_step,t_step).astype(float)

    total_bytes_r = 0#np.sum(np.repeat(t_s,len(b_r))*len(b_r))
    total_bytes_w = 0#np.sum(np.repeat(t_s,len(b_w))*len(b_w))
    total_bytes_b = 0#np.sum(np.repeat(t_s,len(b_b))*len(b_b))


    # set sampling frequency if not set
    if '-f' not in argv:
        argv.extend(['-f', f'{1/t_step}'])
        if verbose:
            console.print(f"[bold green]Sampling rate set to {t_step} sec ({1/t_step:.3f}) Hz[/]")
    # plot
    # quick_plot(t,b_w)

    # adapt for FTIO
    # command line arguments
    argv = [x for x in argv if '.py' not in x and '.csv' not in x]
    if not '-e' in argv:
        argv.extend(['-e', 'no'])

    if verbose:
        console.print(f"Args: {argv}")
    # argv = ['-e', 'mat']

    res_r={}
    res_w={}
    res_b={}
    
    if 'read' in arrays:
        res_r = quick_ftio(argv,b_r,t, total_bytes_r, ranks, 'read',verbose)
    if 'write' in arrays:
        res_w = quick_ftio(argv,b_w,t, total_bytes_w, ranks, 'write',verbose)
    if 'both' in arrays:
        res_b = quick_ftio(argv,b_b,t, total_bytes_b, ranks, 'both',verbose)

    return {"read":res_r,"write":res_w,"both":res_b}


def get_path(argv, verbose=True):

    full_path =''
    # Example usage

    # Check if argv is a string
    if argv and isinstance(argv, str):
        argv = [argv]  # Convert string to a list with one element

    for i in argv:
        if      'csv' in i:
            path = i
            if os.path.isabs(path):
                # full path
                full_path = path
            else:
                # relative path
                full_path = f'{os.getcwd()}/{path}'
            break

    if not full_path:
        full_path = f'{os.getcwd()}/data_2.csv'

    if verbose:
        console.print(f'[green] current file: {full_path}[/]')

    return full_path


def quick_ftio(argv,b,t, total_bytes, ranks, msg, verbose=True) :

    # set up data
    data = {
            'time': t,
            'bandwidth': b,
            'total_bytes': total_bytes,
            'ranks': ranks 
            }

    #parse args
    args = parse_args(argv,'ftio')

    # perform prediction
    prediction, dfs = core([data], args)


    # plot and print info
    convert_and_plot(data, dfs, args)
    if verbose:
        console.print(f'[green]>> Prediction for {msg}[/]')
        display_prediction("ftio", prediction)
    return prediction

if __name__ == "__main__":
    _ = main(sys.argv)