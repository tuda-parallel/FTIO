"""This functions calculates the frequency based on the input data provided. 
Currently darshan, recorder, and traces generated with our internal tool are supported. 

call ftio -h to see list of suppoerted argurmnts. 
"""

from __future__ import annotations
import time
import sys
import numpy as np
from rich.console import Group
from rich.panel import Panel
from ftio.parse.scales import Scales
from ftio.parse.extract import get_time_behavior
from ftio.freq.freq_plot_core import convert_and_plot
from ftio.freq.helper import get_mode, MyConsole
from ftio.freq.autocorrelation import find_autocorrelation
from ftio.freq.anomaly_detection import outlier_detection
from ftio.freq.discretize import sample_data
from ftio.freq._wavelet import wavelet_disc, plot_wave_disc, wavelet_cont, plot_wave_cont#, welch
from ftio.freq._dft import dft, prepare_plot_dfs, display_prediction, precision_dft
from ftio.prediction.unify_predictions import merge_predictions

CONSOLE = MyConsole()


def main(cmd_input: list[str]):# -> dict[Any, Any]:
    """Pass varibales and call main_core. The extraction of the traces
    and the parsing of the arguments is done in this function.
    """
    start = time.time()
    data = Scales(cmd_input)
    data.get_data()
    args = data.args
    df = get_mode(data, args.mode)
    CONSOLE.set(args.verbose)
    CONSOLE.print(f"\n[cyan]Data imported in:[/] {time.time() - start:.2f} s")
    CONSOLE.print(f"[cyan]Frequency Analysis:[/] {args.transformation.upper()}")
    CONSOLE.print(f"[cyan]Mode:[/] {args.mode}")

    data = get_time_behavior(df)
    prediction = {}
    share = {}
    dfs = [[], [], [], []]
    for sim in data:
        # perform frequency anylsis (dft/wavelet)
        prediction_dft, dfs, share = freq_analysis(args, sim)
        # Perform autocorrelation if args.autocorrelation is true + Merge the results into a single prediction
        prediction_auto = find_autocorrelation(args, sim, share)
        prediction = merge_predictions(args, prediction_dft, prediction_auto)

    convert_and_plot(data, dfs, args)
    CONSOLE.print(f"[cyan]Total elapsed time:[/] {time.time()-start:.3f} s\n")
    display_prediction(cmd_input, prediction)
    return prediction, args


def freq_analysis(args, data: dict) -> tuple[dict, tuple[list, list, list, list], dict]:
    """Discription:
    performs sampling and that frequency technique (dft, wave_cont, or wave_disc),
    followed by creating
    a datframe with the information for plotting

    Args:
        args (argparse): see io_args.py
        data (dict): containing 4 fields:
            1. bandwidth (np.array): bandwidth array
            2. time (np.array): time array indicating when bandwidth time points chaged
            3. total_bytes (int): total transferred bytes
            4. ranks: number of ranks that did I/O

    Raises:
        Exception: _description_

    Returns:
        dict: Conating the predicition with the following fields:
            1. dict:  Containing result of prediction includeing: 
                "dominant_freq" (list), "conf" (np.array), "t_start" (int), "t_end" (int), "total_bytes" (int).
            2. tuple[list, list, list, list]: for plot
            3. dict: Conating sampled data including:
                b_sampled, "freq", "t_start", "t_end", "total_bytes"
    """
    k = 0
    share = {}
    df_out = [[], [], [], []]
    prediction = {
        "source": {args.transformation},
        "dominant_freq": [],
        "conf": [],
        "t_start": 0,
        "t_end": 0,
        "total_bytes": 0,
        "freq": 0,
        "ranks": 0,
    }
    bandwidth = data["bandwidth"] if "bandwidth" in data else np.array([])
    time_b = data["time"] if "time" in data else np.array([])
    total_bytes = data["total_bytes"] if "total_bytes" in data else 0
    ranks = data["ranks"] if "ranks" in data else 0
    text = f"Ranks: [cyan]{ranks}[/]\n"
    ignored_bytes = total_bytes

    if args.ts:  # shorten data
        indecies = np.where(time_b >= args.ts)
        time_b = time_b[indecies]
        bandwidth = bandwidth[indecies]
        total_bytes = np.sum(
            bandwidth * (np.concatenate([time_b[1:], time_b[-1:]]) - time_b)
        )
        text += f"[green]Start time set to {args.ts:.2f}[/] s\n"
    else:
        text += f"Start time: [cyan]{time_b[0]:.2f}[/] s \n"

    if args.te:  # shorten data
        indecies = np.where(time_b <= args.te)
        time_b = time_b[indecies]
        bandwidth = bandwidth[indecies]
        total_bytes = np.sum(
            bandwidth * (np.concatenate([time_b[1:], time_b[-1:]]) - time_b)
        )
        text += f"[green]End time set to {args.te:.2f}[/] s\n"
    else:
        text += f"End time: [cyan]{time_b[-1]:.2f}[/] s\n"

    ignored_bytes = (ignored_bytes - total_bytes)
    text += f"Total bytes: [cyan]{total_bytes:.2e} bytes[/]\n"
    text += f"Ignored bytes: [cyan]{ignored_bytes:.2e} bytes[/]\n"
    tik = time.time()
    CONSOLE.print("[cyan]Executing:[/] Discretization\n")

    #! Discretize signal
    # sample the bandwidth bandwidth
    b_sampled, freq, text_disc = sample_data(bandwidth, time_b, args.freq)  
    CONSOLE.print(Panel.fit(text_disc, style="white", border_style='yellow', title="Discretization", title_align='left'))
    CONSOLE.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")
    CONSOLE.print(f"[cyan]Executing:[/] {args.transformation.upper()} + {args.outlier}\n")
    tik = time.time()

    #! Choose Method
    if "dft" in args.transformation:
        # calculate DFT
        X = dft(b_sampled)
        N = len(X)
        amp = abs(X)  

        # welch(bandwidth,freq)
        freq_arr = freq * np.arange(0, N) / N
        phi = np.arctan2(X.imag, X.real)
        conf = np.zeros(len(amp))

        # Find dominant frequency
        (
            dominant_index,
            conf[1 : int(len(amp) / 2) + 1],
            outlier_text,
        ) = outlier_detection(amp, freq_arr, args)

        conf[0] = np.inf
        if len(amp) % 2 == 0:
            conf[int(len(amp) / 2) + 1 :] = np.flip(conf[1 : int(len(amp) / 2)])
        else:
            conf[int(len(amp) / 2) + 1 :] = np.flip(conf[1 : int(len(amp) / 2) + 1])

        prediction["dominant_freq"] = freq_arr[dominant_index]
        prediction["conf"] = conf[dominant_index]
        prediction["t_start"] = time_b[0]
        prediction["t_end"] = time_b[-1]
        prediction["total_bytes"] = total_bytes
        prediction["freq"] = freq
        prediction["ranks"] = ranks

        if args.autocorrelation:
            share["b_sampled"] = b_sampled
            share["freq"] = freq
            share["t_start"] = prediction["t_start"]
            share["t_end"] = prediction["t_end"]
            share["total_bytes"] = prediction["total_bytes"]

        precision_text = ""
        # precision_text = precision_dft(
        #     amp, phi, dominant_index, b_sampled, time_b[0] + np.arange(0, N) * 1 / freq, freq_arr, args.engine
        # )

        text = Group(text, outlier_text, precision_text[:-1])

        if any(x in args.engine for x in ["mat","plot"]):
            df_out = prepare_plot_dfs(
                k,
                freq,
                freq_arr,
                conf,
                dominant_index,
                amp,
                phi,
                b_sampled,
                time_b,
                ranks,
                N,
                bandwidth,
            )
        k += 1

    elif "wave_disc" in args.transformation:
        # discrete wavlet decomposition:
        # https://edisciplinas.usp.br/pluginfile.php/4452162/mod_resource/content/1/V1-Parte%20de%20Slides%20de%20p%C3%B3sgrad%20PSI5880_PDF4%20em%20Wavelets%20-%202010%20-%20Rede_AIASYB2.pdf
        # https://www.youtube.com/watch?v=hAQQwvKsWCY&ab_channel=NathanKutz
        print("    '-> \033[1;32mPerforming discret wavelet decomposition\033[1;0m")
        wavelet = "db1"  # dmey might be better https://pywavelets.readthedocs.io/en/latest/ref/wavelets.html
        # wavelet = 'haar' # dmey might be better https://pywavelets.readthedocs.io/en/latest/ref/wavelets.html
        coffs = wavelet_disc(b_sampled, wavelet, args.level)
        cc, f = plot_wave_disc(
            b_sampled, coffs, time_b, args.freq, args.level, wavelet, bandwidth
        )
        for fig in f:
            fig.show()
        cont = input("\nContinue with the DFT? [y/n]")

        if len(cont) == 0 or "y" in cont.lower():
            args.transformation = "dft"
            n = len(b_sampled)
            tmp = {
                "time": time_b[0] + 1 / freq * np.arange(0, n),
                "bandwidth": cc[0],
                "total_bytes": total_bytes,
                "ranks": ranks,
            }
            freq_analysis(args, tmp)

        sys.exit()

    elif "wave_cont" in args.transformation:
        # Continous wavelets
        print("    '-> \033[1;32mPerforming discret wavelet decomposition\033[1;0m")
        wavelet = "morl"
        # wavelet = 'cmor'
        # wavelet = 'mexh'
        [coefficients, frequencies, scale] = wavelet_cont(
            b_sampled, wavelet, args.level, args.freq
        )
        fig = plot_wave_cont(
            b_sampled, frequencies, args.freq, scale, time_b, coefficients
        )
        sys.exit()

    else:
        raise Exception("Unsupported decomposition specified")
    CONSOLE.print(
        Panel.fit(
            text,
            style="white",
            border_style="cyan",
            title=args.transformation.upper(),
            title_align="left",
        )
    )
    CONSOLE.print(
        f"\n[cyan]{args.transformation.upper()} + {args.outlier} finished:[/] {time.time() - tik:.3f} s"
    )
    return prediction, df_out, share


def run():
    _ = main(sys.argv)


if __name__ == "__main__":
    _ = main(sys.argv)
