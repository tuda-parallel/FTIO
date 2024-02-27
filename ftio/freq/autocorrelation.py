from __future__ import annotations
import time
import numpy as np
from scipy.signal import find_peaks
from rich.panel import Panel
import plotly.graph_objects as go
# from rich.padding import Padding
import ftio.freq.discretize as dis
from ftio.freq.helper import format_plot
from ftio.freq.helper import MyConsole


# PLOT_MODE = "on"
# try:
# except ImportError:
#     PLOT_MODE = "empty"

CONSOLE = MyConsole()

def find_autocorrelation(args, data: dict, share:dict) -> dict:
    """Finds perodicity using autocorreleation

    Args:
        args (argparse): command line arguments
        data (dict): sampled data

    Returns:
        dict: predictions containing 4 fields: 
            1. bandwidth (np.array): bandwidth array
            2. time (np.array): time array indicating when bandwidth time points chaged
            3. total_bytes (int): total transferred bytes
            4. ranks: number of ranks that did I/O
    """
    prediction = {}
    candidates = np.array([])
    fig = []
    CONSOLE.set(args.verbose)
    tik = time.time()
    if args.autocorrelation:
        CONSOLE.print("[cyan]Executing:[/] Autocorrelation\n")
        prediction = {
        "source":"autocorrelation",
        "dominant_freq": [],
        "conf": [],
        "t_start": 0,
        "t_end": 0,
        "total_bytes": 0,
        }
        # print("    '-> \033[1;32mExecuting Autocorrelation")
        b_sampled = np.array([])
        freq = np.NaN
        t_s = np.NaN
        t_e = np.NaN
        total_bytes = np.NaN
        # Ckeck if figure is on
        if any(x in args.engine for x in ["mat","plot"]):
            fig.append(go.Figure())

        # Take data if already avilable from previous step
        if share:
            b_sampled = share["b_sampled"]
            freq = share["freq"]
            t_s = share["t_start"]
            t_e = share["t_end"]
            total_bytes = share["total_bytes"]
        else:
            total_bytes = 0
            bandwidth = data["bandwidth"] if "bandwidth" in data else np.array([])
            time_b = data["time"] if "time" in data else np.array([])
            t_s = time_b[0]
            t_e = time_b[-1]
            if args.ts:  # shorten data
                time_b = time_b[time_b >= args.ts]
                t_s = time_b[0]
                bandwidth = bandwidth[len(bandwidth) - len(time_b) :]
                total_bytes = np.sum(
                    bandwidth * (np.concatenate([time_b[1:], time_b[-1:]]) - time_b)
                )
                CONSOLE.print(f"[purple]Start time set to {args.ts:.2f}")
            else:
                CONSOLE.print(f"[purple]Start time: {time_b[0]:.2f}")

            if args.te:  # shorten data
                time_b = time_b[time_b <= args.te]
                t_s = time_b[-1]
                bandwidth = bandwidth[len(bandwidth) - len(time_b) :]
                total_bytes = np.sum(
                    bandwidth * (np.concatenate([time_b[1:], time_b[-1:]]) - time_b)
                )
                CONSOLE.print(f"[purple]End time set to {args.te:.2f}")
            else:
                CONSOLE.print(f"[purple]End time: {time_b[-1]:.2f}")

            # sample the bandwidth bandwidth
            b_sampled, freq, text = dis.sample_data(bandwidth, time_b, args.freq) 
            CONSOLE.print(Panel.fit(text, style="white", border_style='yellow', title="Discretization", title_align='left'))

        # Scipy autocorrelation
        # lags = range(int(freq*len(b_sampled)))
        # acorr = sm.tsa.acf(b_sampled, nlags = len(lags)-1)
        #! numpy autocorrelation
        # # Mean
        mean = np.mean(b_sampled)
        # Variance
        var = np.var(b_sampled)
        # Normalized data
        ndata = b_sampled - mean
        # Caclualte autocorrelation:
        acorr = np.correlate(ndata, ndata, "full")[len(ndata) - 1 :]
        acorr = acorr / var / len(ndata)
        # plot
        if any(x in args.engine for x in ["mat","plot"]):
            fig[-1].add_scatter(y=acorr, mode="markers+lines", name="ACF", 
                                marker=dict(
                                            color = acorr,
                                            colorscale = ["rgb(0,50,150)", "rgb(150,50,150)", "rgb(255,50,0)"],
                                            showscale = True
                                            ))
            fig[-1].update_layout(
                font={"family": "Courier New, monospace", "size": 24, "color": "black"},
                xaxis_title="Lag (Samples)",
                yaxis_title="ACF",
                width = 1100,
                height = 400 #500
                )
            fig[-1].update_layout(coloraxis_colorbar=dict(yanchor="top", y=1, x=0, ticks="outside", ticksuffix=" bills"))
            # fig[-1].update_layout(legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.01))
            fig[-1].update_layout(legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99))
            fig[-1] = format_plot(fig[-1])
            fig[-1].show()

        #! finding peak locations and calc the average time differences between them:
        peaks, prop  = find_peaks(acorr, height=0.15)
        candidates = np.diff(peaks) / freq
        weights = np.diff(prop['peak_heights'])
        # weights = []
        # heights = prop['peak_heights']
        # for i,_ in enumerate(heights):
        #     if i != len(heights) - 1:
        #         weights.append(abs(prop['peak_heights'][i+1]) +abs(prop['peak_heights'][i]))
        # weights = np.array(weights)
        # if len(weights) > 0:
        #     weights = weights/np.sum(weights)
        # print(peaks)
        # print(heights)
        # print(weights)
        
        if "mat" in args.engine or "plotly" in args.engine:
            fig[-1].add_scatter(
                x=peaks,
                y=acorr[peaks],
                marker=dict(
                    color = "rgba(20, 220, 70, 0.9)",
                    size=14, #12,
                    symbol="star-triangle-up",
                    angle=0,
                    line=dict(width=1, color="DarkSlateGrey")
                ),
                mode="markers",
                name="peaks",
            )

        # finde outliers
        text  = ""
        outliers, text = filter_outliers(freq, candidates, weights)
        # remove outliers
        if len(outliers) != 0:
            candidates = np.delete(candidates, outliers)
            weights = np.delete(weights, outliers)
        # calculate period
        mean = np.average(candidates, weights=weights) if len(weights) > 0 else 0 
        std =  np.sqrt(np.abs(np.average((candidates-mean)**2, weights=weights))) if len(weights) > 0 else 0
        tmp = 1 / candidates if len(candidates) > 0 and any(candidates > 0) else 0
        if isinstance(tmp,list) and len(tmp) > 0:
            tmp = [f"{i:.4f}" for i in tmp]

        text += f"Found perodicities are [purple]{candidates}[/]\n"
        text += f"Matching Frequncies are [purple]{tmp}[/]\n"
        periodicity = mean if len(candidates) > 0 else np.nan
        text += f"Average petrodicity is [purple]{periodicity:.2f} [/]sec\n"
        text += f"Average frequency is [purple]{1/periodicity if periodicity > 0 else np.nan:.4f} [/]Hz\n"

        # calculate confidence using "Coefficient of variation": https://en.wikipedia.org/wiki/Coefficient_of_variation
        coef_var = np.abs(std / mean ) if len(candidates) > 0 else np.nan
        # coef_var = np.abs(np.std(candidates) / np.mean(candidates) ) if len(candidates) > 0 else np.nan
        conf = np.abs(1 - coef_var)
        text += f"confidence is [purple]{conf*100:.2f} [/]%\n"
        
        # CONSOLE.print(Padding(Panel.fit(text[:-1], style="white", border_style='purple', title="Autocorreleation", title_align='left'), (0, 4)))
        CONSOLE.print(Panel.fit(text[:-1], style="white", border_style="purple", title="Autocorreleation", title_align="left"))

        if "mat" in args.engine or "plotly" in args.engine:
            if len(candidates) > 0:
                val = np.delete(peaks,outliers)
                fig[-1].add_scatter(
                    x=val,
                    y=acorr[val],
                    marker=dict(
                        color = "rgba(220, 20, 70, 0.9)",
                        size=21, #19,
                        symbol="circle-open-dot",
                        angle=0,
                        line=dict(width=2, color="DarkSlateGrey")
                    ),
                    mode="markers",
                    name="relevant peaks",
                )
            fig[-1] = format_plot(fig[-1])
            fig[-1].show(config = {"toImageButtonOptions": {"format": "png", "scale": 5}})

        prediction["dominant_freq"] = 1/periodicity  if periodicity > 0 else np.nan
        prediction["conf"] = conf
        prediction["t_start"] = t_s
        prediction["t_end"] = t_e
        prediction["total_bytes"] = total_bytes
        prediction["freq"] = freq
        prediction["candidates"] = candidates
        CONSOLE.print(f"\n[cyan]Autocorrelation finished:[/] {time.time() - tik:.3f} s")
        
    return prediction


def filter_outliers(freq: float, candidates: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, str]:
    """removes outliers using either qunatil method or Z-score

    Args:
        candidates (np.ndarray): peaks
        weights (np.ndarray): weights of the peaks

    Returns:
        np.ndarray: outliers
        str: string text
    """
    text = ""
    outliers = np.array([])
    # remove outliers:
    if len(candidates) > 0 and any(candidates > 0):
        ind = np.where(candidates > 1/freq)
        candidates = candidates[ind] # remove everythin above 10 Hz
        if len(weights > 0):
            weights = weights[ind]
        method = "z"
        # With quantil and weights
        if "q" in method:
            text += f"Filtering method: [purple]quantil[/]\n"
            # candidates = candidates*weights/sum(weights)
            q1 = np.percentile(candidates, 25)
            q3 = np.percentile(candidates, 75)
            iqr = q3 - q1
            threshold = 1.5 * iqr
            outliers = np.where(
                (candidates < q1 - threshold) | (candidates > q3 + threshold)
            )
        elif "z" in method:
            text += "Filtering method: [purple]Z-score with weighteed mean[/]\n"
            # With Zscore:
            mean = np.average(candidates, weights=weights) if len(weights) > 0 else 0
            # std = np.std(candidates)
            std =  np.sqrt(np.abs(np.average((candidates-mean)**2, weights=weights))) if len(weights) > 0 else 0
            text += f"Wighted mean is [purple]{mean:.3f}[/] and weighted std. is [purple]{std:.3f}[/]\n"
            z_score = np.abs((candidates - mean) / std) if std != 0  else np.array([])
            outliers = np.where(z_score > 1)
            text += f"Z-score is [purple]{print_array(z_score)}[/]\n"
        
        text += (
            f"[purple]{len(candidates)}[/] period candidates found:\n"
            f"[purple]{print_array(candidates)}[/]\n\n"
            f"{len(candidates[outliers])} outliers found:\n[purple]{print_array(candidates[outliers])}[/]\n\n"
        )
    else:
        text += "[purple]Empty[/]\n"

    return outliers, text

def print_array(array:np.ndarray) -> str:
    out = ""
    if len(array) == 0:
        out =" "
    for i in array:
        out += f" {i:.2f}"
    

    return "["+out[1:]+"]"
