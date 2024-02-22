"""Merge Predections

"""
from __future__ import annotations
import time
import numpy as np
from rich.panel import Panel
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()

def merge_predictions(args, pred_dft:dict, pred_auto:dict)-> dict:
    """Merge prediction if both autocorrelation and freq. technique (dft/wavelet) are executed

    Args:
        args (_type_): _description_
        pred_dft (dict): prediction frequency technqiue
        pred_auto (dict): prediction autocorrelation

    Returns:
        dict: merge prediction
    """
    CONSOLE.set(args.verbose)
    pred_merged = pred_dft.copy()
    if args.autocorrelation:
        tik = time.time()
        CONSOLE.print(f"[cyan]Merging Started:[/]\n")
        text = f"Merging Autocorrelation and {args.transformation.upper()}\n"
        if pred_auto and  not np.isnan(pred_auto["dominant_freq"]):
            pred_merged["dominant_freq"], pred_merged["conf"], text = merge_core(pred_dft, pred_auto, args.freq, text)
            if pred_merged["dominant_freq"]:
                text += f"Dominant frequency: [blue bold]{np.round(pred_merged['dominant_freq'][-1],4)}[/] Hz -> [blue bold]{np.round(1/pred_merged['dominant_freq'][-1],4)}[/] sec\n"
                text += f"Confidence: [bold]{color_pred(pred_merged['conf'][-1])}{np.round(pred_merged['conf'][-1]*100,2)}[/] %\n"
            pred_auto.pop("candidates", None)
        else:
            text += "[yellow]Autrocorrelation prediction is empty[/]\n"
        CONSOLE.print(Panel.fit(text[:-1], style="white", border_style="blue", title="Merging Predections", title_align='left'))
        CONSOLE.print(f"\n[cyan]Merging finished:[/] {time.time() - tik:.3f} s")

    return pred_merged


def merge_core(pred_dft:dict, pred_auto:dict ,freq:float, text:str) -> tuple[list,list,str]:
    """Merge the predictions

    Args:
        pred_dft (dict): prediction from dft. technique
        pred_auto (dict): prediction from autocorreleation
        freq: sampling frequency
        text (str): display string

    Returns:
        tuple[list,list,str]: dominant frequency, confidence, and display string
    """
    dominant_freq = -1
    conf = 0
    out_freq, out_conf = [],[]
    method = "hits"
    method2 = "cov" # ratio or cov for method hits
    if len(pred_dft["dominant_freq"]) >= 1:
        if "alike" in method:
            alike = (pred_auto["dominant_freq"] - abs(pred_dft["dominant_freq"] - pred_auto["dominant_freq"]))/pred_auto["dominant_freq"]
            text += f"Frequencies [yellow]{np.round(pred_dft['dominant_freq'],4)}[/] Hz match [yellow]{np.round(pred_auto['dominant_freq'],4)}[/] Hz by:\n[yellow]{np.round(alike,4)}[/]%\n\n"
            dominant_index = np.argmax(alike)
            dominant_freq = pred_dft["dominant_freq"][dominant_index]
            conf  = (pred_dft["conf"][dominant_index] + pred_auto["conf"])/2
        elif "hits" in method:
            tol = 2/freq # 2 frequency steps
            hits = np.zeros(len(pred_dft["dominant_freq"]))
            if "ratio" in method:
                alike = np.zeros((len(pred_dft["dominant_freq"]),len(pred_auto["candidates"])))
            else: # cov method
                alike = np.zeros(len(pred_dft["dominant_freq"]))

            # Find perfect hits and caclualte distance of the candiidates to the freq predictions
            for i,f_d in enumerate(pred_dft["dominant_freq"]):
                t_d = 1/f_d
                hits[i] = sum((t_d - tol < pred_auto["candidates"])  & (pred_auto["candidates"] < t_d + tol ))
                if "ratio" in method:
                    alike[i,:] = np.min([pred_auto["candidates"]/t_d, t_d/pred_auto["candidates"]],axis=0) #1 - abs(pred_auto["candidates"] - t_d)/t_d
                else: # cov method
                    alike[i] = 1 - np.abs(np.std(np.append(pred_auto["candidates"],t_d))/np.mean(np.append(pred_auto["candidates"],t_d)))


            # check if there is a predect prediction
            text += f"Perfect hits of [blue]{pred_dft['dominant_freq']}[/] are [blue] {hits}[/]  \n"
            for i,value in enumerate(hits):
                if value == len(pred_auto["candidates"]):
                    text += "[green bold]Perfect Prediction found! [/]\n"
                    dominant_freq = pred_dft["dominant_freq"][i]
                    conf  = 1
                    break

            #No perfect hit, see which better fits
            if "ratio" in method:
                dominant_index = np.argmax(np.sum(alike, axis=1))
            else: # cov method
                dominant_index = np.argmax(alike)
            
            dominant_freq = pred_dft["dominant_freq"][dominant_index]
            # calculate conf:
            agreed_predictions = np.argmax(alike,axis=0)
            if "ratio" in method:
                text += f"Agreed prediction ratio  [blue] {np.sum(alike, axis=1)/len(agreed_predictions)*100}[/] %\n"
                conf = (1 - np.std([pred_dft["conf"][dominant_index],pred_auto["conf"]])/np.mean([pred_dft["conf"][dominant_index],pred_auto["conf"]])
                    + pred_dft["conf"][dominant_index]
                    + pred_auto["conf"]
                    )/3 
            else: 
                text += f"Agreed prediction [blue] {alike*100}[/] %\n"
                conf = (alike[dominant_index] + pred_dft["conf"][dominant_index] + pred_auto["conf"])/3 
                # text += f"[red bold]{alike[dominant_index]} + {pred_dft['conf'][dominant_index]} + {pred_auto['conf']}[/]\n"
                
            if conf >= 0.2:
                out_freq, out_conf = [dominant_freq], [conf]
            else:
                out_freq, out_conf = [], []
                text += "[red bold]Too low confidence, no dominant freq[/]\n"
                
    else:# no dft result
        dominant_freq = pred_auto["dominant_freq"]
        conf = pred_auto["conf"]/3
        text += "Confidence: [red] Warning! Low confidence! [/]\n"
        out_freq, out_conf = [dominant_freq], [conf]

    return out_freq, out_conf, text


def color_pred(conf:float)-> str:
    """highlight color according to value

    Args:
        conf (float): value between [0,1]

    Returns:
        string: color to be used with Console (from rich)
    """
    if conf >= 0.8:
        color = "[green]"
    elif conf >= 0.6:
        color = "[blue]"
    elif conf >= 0.3:
        color = "[yellow]"
    else:
        color = "[red]"
    return color
