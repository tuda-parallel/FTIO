from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.freq.freq_plot_core import convert_and_plot
from ftio.api.metric_proxy.parse_proxy import parse
from ftio.post.processing import label_phases

#---------------------------------
# Modification Area
#---------------------------------
b, t = parse("/d/sim/metric_proxy/traces/Mixed_1x8_5.json", "total___mpi___size_total")
ranks = 32

# command line arguments
argv = ["-e", "plotly"]  #["-e", "no"] to disable the plot
#---------------------------------

# set up data
data= {
        "time": t,
        "bandwidth": b,
        "total_bytes": 0,
        "ranks": ranks 
        }

#parse args
args = parse_args(argv,"ftio")

# perform prediction
prediction, dfs = core([data], args)

# plot and print info
convert_and_plot(data, dfs, args)
display_prediction(["./ftio"], prediction)

# Post processing
if prediction and len(prediction["dominant_freq"])!= 0:
    phases, time = label_phases(prediction,args)

    print(f"phases: {phases}\ntime: {time}\n")