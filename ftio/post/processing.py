import numpy as np
import plotly.graph_objects as go

def label_phases(prediction:dict, args):
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

    return phases, time