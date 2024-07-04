import numpy as np
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.freq.freq_plot_core import convert_and_plot
from ftio.parse.bandwidth import overlap
from ftio.parse.csv_reader import read_csv_file
import os 

# Example usage

full_path = f'{os.getcwd()}/data.csv'
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
prediction, dfs = core([data], args)


# plot and print info
convert_and_plot(data, dfs, args)
display_prediction("ftio", prediction)