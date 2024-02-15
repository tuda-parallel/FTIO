"""Performs the anylsis for prediction. This includes the calculation of ftio and parsing of the data into a queue """
from __future__ import annotations
from multiprocessing import  Queue
from ftio.cli import ftio_core
from ftio.prediction.helper import get_dominant
from rich.console import Console
import numpy as np


def ftio_process(queue: Queue, count, hits, start_time, aggregated_bytes, args) -> None:
    """Perform a single prediction

    Args:

        queue (Manager().Queue): queue for FTIO data
        count (Manager().Value): number of prediction
        hits (Manager().Value): hits indicating how often a dominant frequncy was found
        start_time (Manager().Value): start time window for ftio
        aggregated_bytes (Manager().Value): total bytes transferred so far
        args (list[str]): additional arguments passed to ftio
    """
    console = Console()
    console.print(f"[purple][PREDICTOR] (#{count.value}):[/]  Started")
    # Modify the arguments
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{start_time.value:.2f}"])
    # perform prediction
    prediction, args = ftio_core.main(args)
    # get data
    t_s = prediction["t_start"]
    t_e = prediction["t_end"]
    total_bytes = prediction["total_bytes"]
    freq = get_dominant(prediction) #just get a single dominant value
    hits = get_hits(prediction,count.value,hits)
    # save data
    queue.put(
        {
            "phase": count.value,
            "dominant_freq": prediction["dominant_freq"],
            "conf": prediction["conf"],
            "t_start": prediction["t_start"],
            "t_end": prediction["t_end"],
            "total_bytes": prediction["total_bytes"],
            "ranks": prediction["ranks"],
            "freq": prediction["freq"],
            "hits": hits.value,
        }
    )
    
    text = ""
    if not np.isnan(freq):
        text = f"[purple][PREDICTOR] (#{count.value}):[/] Dominant freq {freq:.3f} \n"

    text += (
        f"[purple][PREDICTOR] (#{count.value}):[/] Time window {t_e-t_s:.3f} sec ([{t_s:.3f},{t_e:.3f}] sec)\n"
        f"[purple][PREDICTOR] (#{count.value}):[/] Total bytes {total_bytes:.3f} B\n"
        f"[purple][PREDICTOR] (#{count.value}):[/] Bytes transferred since last "
        f"time {abs(total_bytes-aggregated_bytes.value):.3f} B\n"
        )
    # safe total transferred bytes
    aggregated_bytes.value = total_bytes
    
    # average data/data processing
    if not np.isnan(freq):
        n_phases = (t_e-t_s)*freq
        avr_bytes = int(total_bytes/float(n_phases))
        #FIXME this needs to compensate for a smaller windows
        if not args.window_adaptation:
            text += (
                f"[purple][PREDICTOR] (#{count.value}):[/] Estimated phases {n_phases:.2f}\n"
                f"[purple][PREDICTOR] (#{count.value}):[/] Average transferred {avr_bytes:.3f} B\n"
            )
        
        # adaptive time window
        if args.window_adaptation:
            if hits.value > args.x_hits: 
                if True: #np.abs(avr_bytes - (total_bytes-aggregated_bytes.value)) < 100:
                    tmp = t_e - 3*1/freq
                    start_time.value = tmp if tmp > 0 else 0
                    aggregated_bytes.value = total_bytes
                    text += f"[purple][PREDICTOR] (#{count.value}):[/][green] Adjsuting start time to {start_time.value} sec\n[/]"
            else:
                start_time.value = 0
                if hits.value == 0:
                    text += f"[purple][PREDICTOR] (#{count.value}):[/][red bold] Resetting start time to {start_time.value} sec\n[/]"
                
    # TODO 1: Make sanity check -- see if the same number of bytes was transferred
    # TODO 2: Train a model to validate the predictions?
    text += f"[purple][PREDICTOR] (#{count.value}):[/] Ended"
    console.print(text)
    count.value += 1


def get_hits(prediction: dict, count: int, hits):
    """Manges the hit variable. In case a dominant frequency is found, hits is increased. 

    Args:
        prediction (dict): predicition up till now
        count (int): number of the predicition
        hits (Value): how often a dominant frequency was found

    Returns:
        hits: increased value if a dominant frequncy was found, otherwise it is reset to 0
    """
    console = Console()
    text = ""
    text += f"[purple][PREDICTOR] (#{count}):[/] Freq candidates: \n"
    for i in range(0,len(prediction['dominant_freq'])):
        text += (
            f"[purple][PREDICTOR] (#{count}):[/]    {i}) "
            f"{prediction['dominant_freq'][i]:.2f} Hz -- conf {prediction['conf'][i]:.2f}\n"
        )
    if  len(prediction["dominant_freq"]) == 1:
        hits.value += 1
        text += f"[purple][PREDICTOR] (#{count}):[/] Current hits {hits.value}\n"
    else:
        hits.value = 0
        text += f"[purple][PREDICTOR] (#{count}):[/][red bold] Reseting hits {hits.value}[/]\n"

    console.print(text[:-1])

    return hits
