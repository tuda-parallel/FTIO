import sys
import os 
from datetime import datetime
import numpy as np
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.freq.freq_plot_core import convert_and_plot
from ftio.parse.csv_reader import read_csv_file
from ftio.api.trace_analysis.helper import quick_plot
from rich.console import Console
console = Console()

def main(argv=sys.argv[1:]):

    full_path = get_path(argv)
    arrays = read_csv_file(full_path)
    b_r = np.array([])
    b_w = np.array([])
    b_b = np.array([])

    # for key, array in arrays.items():
    #     print(f"{key}: {array}")
    print(argv)
    ranks = 10
    if 'read' in arrays:
        b_r = np.array(arrays['read']).astype(float)
        console.print("[bold yellow] No read[/]")
    if 'write' in arrays:
        b_w = np.array(arrays['write']).astype(float)
        console.print("[bold yellow] No write[/]")
    if 'both' in arrays:
        b_b = np.array(arrays['both']).astype(float)
        console.print("[bold yellow] No both[/]")

    if 'timestamp' in arrays:
        entries = [datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f') for ts in arrays['timestamp']]
        t_s = entries[0]
        time_diffs_in_seconds = [(dt - t_s).total_seconds() for dt in entries]
        t = np.array(time_diffs_in_seconds)
    else:
        f_s = 1 #get this value from the name of a file
        t_s = 1/f_s
        t = np.arange(0,len(b_w)*t_s,t_s).astype(float)
        argv.extend(['-f', '1'])
        console.print(f"[bold green] Sampling rate set to {t_s}[/]")
        
    total_bytes_r = 0#np.sum(np.repeat(t_s,len(b_r))*len(b_r))
    total_bytes_w = 0#np.sum(np.repeat(t_s,len(b_w))*len(b_w))
    total_bytes_b = 0#np.sum(np.repeat(t_s,len(b_b))*len(b_b))

    # plot
    # quick_plot(t,b_w)

    # adapt for FTIO
    # command line arguments
    argv = [x for x in argv if '.py' not in x and '.csv' not in x]
    argv.extend(['-e', 'no'])
    print(argv)
    # argv = ['-e', 'mat']


    if 'read' in arrays:
        quick_ftio(argv,b_r,t, total_bytes_r, ranks, 'read')
    if 'write' in arrays:
        quick_ftio(argv,b_w,t, total_bytes_w, ranks, 'write')
    if 'both' in arrays:
        quick_ftio(argv,b_b,t, total_bytes_b, ranks, 'both')


def get_path(argv):

    full_path =''
    # Example usage
    for i in argv:
        if 'csv' in i:
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

    print(f'current file: {full_path}\n')

    return full_path


def quick_ftio(argv,b,t, total_bytes, ranks, msg)-> None:

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
    print(f'Prediction for {msg}')
    display_prediction("ftio", prediction)

if __name__ == "__main__":
    main(sys.argv)