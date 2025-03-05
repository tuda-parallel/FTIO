import os 
import sys
import numpy as np
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.plot.freq_plot import convert_and_plot
from ftio.parse.csv_reader import read_csv_file


def main(argv=sys.argv):
    
    full_path = get_path(argv)
    arrays = read_csv_file(full_path)

    # Print the arrays
    for key, array in arrays.items():
        print(f"{key}: {array}")


    #get frequency from file name
    f_s = 0.1 #get this value from the name of a file
    t_s = 1/f_s

    ranks = 10
    b = np.array(arrays['read']).astype(float)
    t = np.arange(0,len(b)*t_s,t_s).astype(float)
    total_bytes = np.sum(np.repeat(t_s,len(b))*len(b))

    # command line arguments
    argv = ["-e", "no"] #["-e", "mat"]

    # set up data
    data = {
            "time": t,
            "bandwidth": b,
            "total_bytes": total_bytes,
            "ranks": ranks 
            }

    #parse args
    args = parse_args(argv,"ftio")

    # perform prediction
    prediction, dfs = core(data, args)


    # plot and print info
    convert_and_plot(args, dfs, len(data))
    display_prediction("ftio", prediction)


def get_path(argv):
    # Example usage
    if len(argv) > 1:
        path = argv[1]
        if os.path.isabs(path):
            # full path
            full_path = path
        else:
            # relative path
            full_path = f'{os.getcwd()}/{path}'
            print(f'current file: {full_path}')
    else:
        # provide the path manually 
        full_path = f'{os.getcwd()}/data/data.csv'

    print(f'current file: {full_path}')

    return full_path


if __name__ == "__main__":
    main(sys.argv)