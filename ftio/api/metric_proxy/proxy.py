import numpy as np
import plotly.graph_objects as go
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.freq.freq_plot_core import convert_and_plot
from ftio.api.metric_proxy.parse_proxy import parse


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
    only_one = False
    if only_one:
        dominant_index = np.argmax(prediction["conf"])
        conf = prediction["conf"][dominant_index]
        f    = prediction["dominant_freq"][dominant_index]
        amp  = prediction["amp"][dominant_index]
        phi  = prediction["phi"][dominant_index]
        N    =  np.floor((prediction["t_end"] - prediction["t_start"])*prediction["freq"])

        ## create cosine wave
        t = np.arange(prediction["t_start"], prediction["t_end"],1/prediction["freq"])
        cosine_wave = 2*amp/N*np.cos(2*np.pi*f*t+phi)
    else:
        t = np.arange(prediction["t_start"], prediction["t_end"],1/prediction["freq"])
        cosine_wave = np.zeros(len(t))
        for index in range(0,len(prediction["conf"])):
            conf = prediction["conf"][index]
            f    = prediction["dominant_freq"][index]
            amp  = prediction["amp"][index]
            phi  = prediction["phi"][index]
            N    =  np.floor((prediction["t_end"] - prediction["t_start"])*prediction["freq"])

            ## create cosine wave
            cosine_wave = cosine_wave + 2*amp/N*np.cos(2*np.pi*f*t+phi)
        
    ## make square signal
    square_wave = np.zeros(len(cosine_wave))
    top = np.max(cosine_wave)
    for i, x in enumerate(cosine_wave):
        if x > 0:
            square_wave[i] = top
        else:
            square_wave[i] = -top

    ## plot 
    if any(x in args.engine for x in ["mat","plot"]):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=cosine_wave,name="cosine wave"))
        fig.add_trace(go.Scatter(x=t, y=square_wave, name="square wave"))
        fig.show()


    phases = []
    time = []
    for i, x in enumerate(square_wave):
        if i == 0:
            counter = 0
            mem = x 
            phases.append(counter)
            time.append(t[i])
        else:
            if mem == x:
                pass
            else:
                mem = x
                counter += 1 
                phases.append(counter)
                time.append(t[i])

    print(f"phases: {phases}\ntime: {time}\n")