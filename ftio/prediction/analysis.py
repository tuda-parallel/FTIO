"""Performs the analysis for prediction. This includes the calculation of ftio and parsing of the data into a queue """
from __future__ import annotations
from multiprocessing import  Queue
from rich.console import Console
import numpy as np
from ftio.cli import ftio_core
from ftio.prediction.helper import get_dominant, get_hits


def ftio_process(queue: Queue, count, hits, start_time, aggregated_bytes, args, msgs=None) -> None:
    """Perform a single prediction

    Args:

        queue (Manager().Queue): queue for FTIO data
        count (Manager().Value): number of prediction
        hits (Manager().Value): hits indicating how often a dominant frequency was found
        start_time (Manager().Value): start time window for ftio
        aggregated_bytes (Manager().Value): total bytes transferred so far
        args (list[str]): additional arguments passed to ftio
    """
    console = Console()
    console.print(f'[purple][PREDICTOR] (#{count.value}):[/]  Started')
    # Modify the arguments
    args.extend(['-e', 'no'])
    args.extend(['-ts', f'{start_time.value:.2f}'])
    
    # perform prediction
    prediction, args = ftio_core.main(args,msgs)
    
    # get data
    freq = get_dominant(prediction) #just get a single dominant value
    hits = get_hits(prediction,count.value,hits)

    # save prediction results
    save_data(queue, aggregated_bytes, prediction, count, hits)
    # display results
    text = display_result(freq ,prediction ,count, aggregated_bytes)
    # data analysis to decrease window
    text, start_time.value = data_analysis(args, prediction, freq, count, hits, text)
    console.print(text)
    count.value += 1


def data_analysis(args, prediction, freq, count, hits, text:str) -> tuple[str, float]:
    # average data/data processing
    t_s = prediction['t_start']
    t_e = prediction['t_end']
    total_bytes = prediction['total_bytes']
    if not np.isnan(freq):
        n_phases = (t_e-t_s)*freq
        avr_bytes = int(total_bytes/float(n_phases))
        #FIXME this needs to compensate for a smaller windows
        if not args.window_adaptation:
            text += (
                f'[purple][PREDICTOR] (#{count.value}):[/] Estimated phases {n_phases:.2f}\n'
                f'[purple][PREDICTOR] (#{count.value}):[/] Average transferred {avr_bytes:.3f} B\n'
            )
        
        # adaptive time window
        if args.window_adaptation:
            if hits.value > args.frequency_hits: 
                if True: #np.abs(avr_bytes - (total_bytes-aggregated_bytes.value)) < 100:
                    tmp = t_e - 3*1/freq
                    t_s = tmp if tmp > 0 else 0
                    text += f'[purple][PREDICTOR] (#{count.value}):[/][green] Adjusting start time to {t_s} sec\n[/]'
            else:
                t_s = 0
                if hits.value == 0:
                    text += f'[purple][PREDICTOR] (#{count.value}):[/][red bold] Resetting start time to {t_s} sec\n[/]'
                
    # TODO 1: Make sanity check -- see if the same number of bytes was transferred
    # TODO 2: Train a model to validate the predictions?
    text += f'[purple][PREDICTOR] (#{count.value}):[/] Ended'

    return text, t_s


def save_data(queue, aggregated_bytes, prediction, count, hits):
    # safe total transferred bytes
    aggregated_bytes.value = prediction['total_bytes']
    
    # save data
    queue.put(
        {
            'phase': count.value,
            'dominant_freq': prediction['dominant_freq'],
            'conf': prediction['conf'],
            'amp': prediction['amp'],
            'phi': prediction['phi'],
            't_start': prediction['t_start'],
            't_end': prediction['t_end'],
            'total_bytes': prediction['total_bytes'],
            'ranks': prediction['ranks'],
            'freq': prediction['freq'],
            'hits': hits.value,
        }
    )


def display_result(freq: float ,prediction: dict ,count, aggregated_bytes):
    text = ''
    if not np.isnan(freq):
        text = f'[purple][PREDICTOR] (#{count.value}):[/] Dominant freq {freq:.3f} \n'

    text += (
        f'[purple][PREDICTOR] (#{count.value}):[/] Time window {prediction["t_end"]-prediction["t_start"]:.3f} sec ([{prediction["t_start"]:.3f},{prediction["t_end"]:.3f}] sec)\n'
        f'[purple][PREDICTOR] (#{count.value}):[/] Total bytes {prediction["total_bytes"]:.3f} B\n'
        f'[purple][PREDICTOR] (#{count.value}):[/] Bytes transferred since last '
        f'time {abs(prediction["total_bytes"]-aggregated_bytes.value):.3f} B\n'
        )

    return text