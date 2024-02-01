"""This functions calculates the frequency based on the input data provided. 
Currently darshan, recorder, and traces generated with our internal tool are supported. 

call ftio -h to see list of suppoerted argurmnts. 
"""

# Profile call
# python3  -m cProfile -s tottime /d/git/tarraf/tmio/src/python/ftio.py 9216.json -freq=10 -mode=sync_write -transformation=dft -dtw=false -level=2 -engine=no > profile
# python3  -m pyinstrument /d/git/tarraf/tmio/src/python/ftio.py 9216.json -freq=10 -mode=sync_write -transformation=dft -dtw=false -level=2 -engine=no
from __future__ import annotations
import time
import sys
import pandas as pd
import numpy as np
import pywt
from scipy import signal
from rich.console import Group
from rich.panel import Panel
from ftio.ioparse.scales import Scales
from ftio.ioparse.extract import get_time_behavior
from ftio.freq.freq_plot_core import convert_and_plot
from ftio.freq.helper import get_mode, MyConsole
from ftio.freq.autocorrelation import find_autocorrelation
from ftio.freq.anomaly_detection import outlier_detection
from ftio.freq.discretize import sample_data
from ftio.prediction.unify_predictions import merge_predictions, color_pred
from ftio.prediction.helper import get_dominant_and_conf

try:
    import matplotlib.pyplot as plt
except ImportError:
    engine = "empty"

CONSOLE = MyConsole()


def main(cmd_input: list[str] = sys.argv):# -> dict[Any, Any]:
    """Pass varibales and call main_core. The extraction of the traces
    and the parsing of the arguments is done in this function.
    """
    start = time.time()
    data = Scales(cmd_input)
    data.get_data()
    args = data.args
    CONSOLE.set(args.verbose)
    df = get_mode(data, args.mode)
    CONSOLE.print(f"\n[cyan]Data imported in:[/] {time.time() - start:.2f} s")
    CONSOLE.print(f"[cyan]Frequency Analysis:[/] {args.transformation}")
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
    CONSOLE.print(f"[cyan]Total ellapsed time:[/] {time.time()-start:.3f} s\n")
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
    text += f"[cyan]Ignored bytes: {ignored_bytes:.6f}[/]\n"
    
    tik = time.time()
    CONSOLE.print("[cyan]Executing:[/] Discretization\n")
    # sample the bandwidth bandwidth
    b_sampled, freq, text = sample_data(bandwidth, time_b, args.freq)  
    CONSOLE.print(Panel.fit(text, style="white", border_style='yellow', title="Discretization", title_align='left'))
    
    CONSOLE.print(f"\n[cyan]Discretization finished:[/] {time.time() - tik:.3f} s")
    CONSOLE.print(
        f"[cyan]Executing:[/] {args.transformation.upper()} + {args.outlier}\n"
    )
    tik = time.time()

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

        time_disc = time_b[0] + np.arange(0, N) * 1 / freq  # discrete time
        precision_text = precision_dft(
            amp, phi, dominant_index, b_sampled, time_disc, freq_arr, args.engine
        )

        text = Group(text, outlier_text, precision_text[:-1])

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
            title=args.transformation.capitalize(),
            title_align="left",
        )
    )
    CONSOLE.print(
        f"\n[cyan]{args.transformation.upper()} + {args.outlier} finished:[/] {time.time() - tik:.3f} s"
    )
    return prediction, df_out, share


def welch(b, freq):
    """Welch method for spectral density estimation.

    Args:
        b (list[float]): bandwidth over time
        freq (float): sampling frequency
    """
    # f, Pxx_den = signal.welch(b, freq, 'flattop', 10000, scaling='spectrum', average='mean')
    f, Pxx_den = signal.welch(
        b, freq, "flattop", freq * 256, scaling="spectrum", average="mean"
    )
    plt.semilogy(f, np.sqrt(Pxx_den))
    plt.xlabel("frequency [Hz]")
    # plt.ylabel('PSD [V**2/Hz]')
    plt.ylabel("Linear spectrum [V RMS]")
    plt.show()


def dft(b):
    return numpy_dft(b)


def dft_fast(b):
    N = len(b)
    X = np.repeat(complex(0, 0), N)  # np.zeros(N)
    for k in range(0, N):
        for n in range(0, N):
            X[k] = X[k] + b[n] * np.exp((-2 * np.pi * n * k / N) * 1j)
    return X


def numpy_dft(b):
    return np.fft.fft(b)


def dft_slow(b):
    N = len(b)
    n = np.arange(N)
    k = n.reshape((N, 1))
    e = np.exp(-2j * np.pi * k * n / N)
    X = np.dot(e, b)
    return X


# Wavelet
# ----------
def wavelet_cont(b_sampled, wavelet, level, freq):
    # Continouse wavelet:
    n = len(b_sampled)
    if isinstance(level, str) and "auto" in level:
        level = pywt.dwt_max_level(n, wavelet)  # pywt.dwt_max_level(n,wavelet)
    else:
        level = int(level)
    print("    '-> \033[1;32mDecomposition level is %d\033[1;0m" % level)
    # [coefficients, frequencies] = pywt.cwt(b_sampled, np.arange(1,5), 'morl')
    # scale = pywt.frequency2scale('morl', np.array([1,10,100])/freq)
    # scale = pywt.frequency2scale('morl', np.arange(freq/100,freq)/freq)
    # scale = 2**np.arange(0,level) #2** mimcs the DWT
    scale = np.arange(1, level)  # 2** mimcs the DWT

    check_wavelet(wavelet, "continuous")
    print(pywt.scale2frequency(wavelet, scale) / (1 / freq))

    [coefficients, frequencies] = pywt.cwt(
        b_sampled, scale, wavelet, sampling_period=1 / freq
    )
    return coefficients, frequencies, scale


def plot_wave_cont(b_sampled, frequencies, freq, scale, t, coefficients):
    time_disc = t[0] + 1 / freq * np.arange(0, len(b_sampled))
    power = (
        abs(coefficients)
    ) ** 2  # probably error on https://ataspinar.com/2018/12/21/a-guide-for-using-the-wavelet-transform-in-machine-learning/
    counter = 0
    for (
        i
    ) in (
        scale
    ):  # see Continuous wavelet transform properties @ https://en.wikipedia.org/wiki/Continuous_wavelet_transform
        power[counter] = 1 / i * power[counter]
        counter = counter + 1
    fig, ax = plt.subplots(figsize=(12, 4))
    im = ax.contourf(
        time_disc,
        frequencies,
        power,
        np.arange(0, power.max(), power.max() / 10),
        extend="neither",
        cmap=plt.cm.seismic,
    )
    # fig.colorbar(im, cax=cbar_ax, orientation="vertical")
    fig.colorbar(im, ax=ax)
    ax.set_ylabel("Frequency (Hz)", fontsize=18)
    ax.set_xlabel("Time (s)", fontsize=18)
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)
    fig.tight_layout()
    plt.show()
    return fig


def wavelet_disc(b_sampled, wavelet, level):
    # Discrete Wavelet:
    check_wavelet(wavelet, "discrete")
    if isinstance(level, str) and "auto" in level:
        level = pywt.dwt_max_level(
            len(b_sampled), wavelet
        )  # pywt.dwt_max_level(n,wavelet)
    else:
        level = int(level)
    print("    '-> \033[1;32mDecomposition level is %d\033[1;0m" % level)
    coffs = pywt.wavedec(b_sampled, wavelet, level=level)
    return coffs


def plot_wave_disc(b_sampled, coffs, t, freq, level, wavelet, b):
    n = len(b_sampled)
    time_disc = t[0] + 1 / freq * np.arange(0, n)
    reconstructed_signal = pywt.waverec(coffs, wavelet, "smooth")
    f = []
    f1 = plt.figure(figsize=(12, 4))
    plt.plot(t, b, label="signal")
    plt.plot(
        time_disc,
        reconstructed_signal[0 : len(time_disc)],
        label="reconstructed levels %d" % level,
        linestyle="--",
    )
    # plt.plot(time,reconstructed_signal[0:len(time)], label='reconstructed levels %d', linestyle='--')
    plt.legend(loc="upper right")
    plt.title("single reconstruction", fontsize=20)
    plt.xlabel("time axis", fontsize=16)
    plt.ylabel("Amplitude", fontsize=16)

    # ? use recon or coffs to either create the paritallly reconstructed signal or the cofficent of the DTW:
    # ? recon -> idea is that all values are extracted just before reconstructing the signal. This adds less resolution to the upper frequencies
    # ? x ---->.g -->↓ 2 --> C1 --> ↑2 -->* g-1  #   captuere   # -->+ --> x
    # ?     '->.h -->↓ 2 --> C2 --> ↑2 -->* h-1  #      here    #  --^
    use = "recon"
    # use = 'coffs' #hold the signal, not upsample!
    cc = np.zeros((level + 1, n))
    for i in np.arange(start=level, stop=0, step=-1):
        # coffs ->  [cA_n, cD_n, cD_n-1, …, cD2, cD1]
        # reconstruction by 1) upsampling and 2) multiplying with the appropiate filter
        # page 29 on https://www.corsi.univr.it/documenti/OccorrenzaIns/matdid/matdid358630.pdf
        # GoH0+G1H1 = 1 -> Multiply a with H1 and d with G1
        # https://medium.com/@shouke.wei/process-of-discrete-wavelet-transform-iii-wavelet-partial-reconstruction-ca7a8f9420dc
        if "recon" in use:
            cc[level - i + 1] = pywt.upcoef(
                "d", coffs[level - i + 1], wavelet, level=i
            )[:n]
        else:
            # Wrong: only upsample: ‘↑ 2’ denotes ‘upsample by 2’ (put 0’s before values)
            # cc[level-i+1,::2**(i)] = coffs[level-i+1]
            # Correct: upsample is used for reconstruction, we only want to visualize -> hold the data constatnt during sample step

            counter = 0
            for j in range(0, n):
                if j % 2**i == 0:
                    cc[level - i + 1, j] = coffs[level - i + 1][counter]
                    counter = counter + 1
                else:
                    cc[level - i + 1, j] = cc[level - i + 1, j - 1]

    if "recon" in use:
        cc[0] = pywt.upcoef("a", coffs[0], wavelet, level=level)[:n]
        fig, ax = plt.subplots(nrows=level + 2, ncols=1, figsize=(12, 12))
        ax[0].plot(t, b, label="signal")
        for i in range(0, level + 1):
            if i == 0:
                sum = cc[0]
            else:
                sum = sum + cc[i]
        ax[0].plot(time_disc, sum, label="sum")
        for i in np.arange(start=level, stop=0, step=-1):
            ax[level - i + 2].plot(time_disc, cc[level - i + 1])
            ax[level - i + 2].set_title(
                f"reconstruction at level {i} from detailed coff -> [{freq / 2 ** (i + 1)}, {freq / 2**i}] Hz"
            )
        ax[1].plot(time_disc, cc[0])
        ax[1].set_title(
            f"reconstruction at level {level} from approximated coff -> [0, {freq / 2 ** (level + 1)}] Hz"
        )
        fig.legend()
        fig.tight_layout()
        f.append(fig)

    else:
        counter = 0
        for j in range(0, n):
            if j % 2**level == 0:
                cc[0, j] = coffs[0][counter]
                counter = counter + 1
            else:
                cc[0, j] = cc[0, j - 1]

    # Use freq or level to plot either the frequency or the level in the y-axis
    show = "freq"
    f_2 = plt.figure(figsize=(12, 4))
    plt.xlabel("Time (s)", fontsize=18)
    # plt.title('Discrete Wavelet Transform with %d decompositions'%level)
    if "freq" in show:
        plt.ylabel("Frequency (Hz)", fontsize=18)
        plt.xticks(fontsize=18)
        plt.yticks(fontsize=18)
        y = np.concatenate(
            [np.array([0]), freq / 2 ** np.arange(start=level + 1, stop=0, step=-1)]
        )
        x = (
            -2 / freq + t[0] + 1 / freq * np.arange(0, len(b_sampled) + 1)
        )  # ? add corner shifted by half a sample step
        X, Y = np.meshgrid(x, y)
        # plt.pcolormesh(X, Y,abs(cc),cmap=plt.cm.coolwarm,shading='flat')
        plt.pcolormesh(X, Y, abs(cc), cmap=plt.cm.seismic, shading="flat")
    else:
        y = np.arange(start=level, stop=-1, step=-1)
        x = t[0] + 1 / freq * np.arange(0, len(b_sampled))
        X, Y = np.meshgrid(x, y)
        plt.pcolormesh(X, Y, abs(cc), cmap=plt.cm.coolwarm)
        plt.ylabel("decomposition level")
        # cc = np.flip(cc,0)
        plt.gca().invert_yaxis()

    # plt.pcolormesh(X, Y, cc,cmap=plt.cm.seismic)
    # plt.pcolormesh(X, Y,abs(cc),cmap=plt.cm.seismic,shading='flat')
    # plt.plot(X.flat, Y.flat, 'x', color='m')
    plt.colorbar()
    f.append(f_2)
    plt.tight_layout()
    f.append(f1)
    return cc, f


def check_wavelet(wavelet, mode="discrete"):
    """check that the wavelet selected is supported

    Args:
        wavelet (str): wavelet name
        mode (str, optional): Wavelet mode. Defaults to "discrete".

    Raises:
        Exception: exits the program on unsupported mode
    """
    check = False
    for supported_wavelet in pywt.wavelist(kind=mode):
        if wavelet == supported_wavelet:
            check = True
            break
    if check is False:
        raise ValueError(
            "Unsupported wavelet specified, suported modes are: %s\nsee: https://pywavelets.readthedocs.io/en/latest/ref/wavelets.html "
            % pywt.wavelist(kind=mode)
        )
        # sys.exit()
    else:
        return


def precision_dft(
    amp, phi, dominant_index, b_sampled, t_disc, freq_arr, plt_engine
) -> str:
    # calculates the precision of the dft
    showplot = False
    text = ""
    if showplot and ("mat" in plt_engine or "plotly" in plt_engine):
        plt.figure(figsize=(10, 5))
    dc_offset = np.zeros(len(amp))
    for index in dominant_index:
        x = dc_offset + 2 * (1 / len(amp)) * amp[index] * np.cos(
            2 * np.pi * np.arange(0, len(amp)) * (index) / (len(amp)) + phi[index]
        )
        x[x < 0] = 0
        x_2 = x.copy()
        total = np.sum(b_sampled)
        for i, _ in enumerate(x):
            if x[i] > b_sampled[i]:
                x_2[i] = b_sampled[i]
                x[i] = -x[i] + b_sampled[i]

        # print(
        #     f"        '-> \033[1;32mPrecision of {freq_arr[index]:.2f} Hz "
        #     f"is {float(np.sum(x)) / total * 100:.2f}%% "
        #     f"(Positive only: {float(np.sum(x_2)) / total * 100:.2f}%%)\033[1;0m"
        # )
        # text += f"Precision of [cyan]{freq_arr[index]:.2f}[/] Hz is [cyan]{float(np.sum(x)) / total * 100:.2f}% [/]"
        # text += f"(Positive only: [cyan]{float(np.sum(x_2)) / total * 100:.2f}%[/])\n"

        if showplot and ("mat" in plt_engine or "plotly" in plt_engine):
            plt.plot(t_disc, x, label=f"f = {freq_arr[index]:.2f} Hz")

    if showplot and ("mat" in plt_engine or "plotly" in plt_engine):
        plt.plot(t_disc, b_sampled, label="b_sampled")
        plt.ticklabel_format(axis="y", style="sci", scilimits=(-5, 3))
        plt.ticklabel_format(axis="x", style="sci", scilimits=(-5, 3))
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        plt.ylabel("Amplitude (MB/s)", fontsize=17)
        plt.xlabel("Time (s)", fontsize=17)
        plt.grid(True)
        plt.legend(loc="upper left", ncol=2, fontsize=13)
        plt.tight_layout()
        plt.show()

    return text


def prepare_plot_dfs(
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
) -> tuple[list, list, list, list]:
    df0 = []
    df1 = []
    df2 = []
    df3 = []
    df3.append(
        pd.DataFrame(
            {
                "dominant": freq_arr[dominant_index],
                "k": dominant_index,
                "conf": conf[dominant_index],
                "ranks": np.repeat(ranks, len(dominant_index)),
            }
        )
    )
    df0.append(
        pd.DataFrame(
            {
                "A": amp,
                "phi": phi,
                "b_sampled": b_sampled,
                "ranks": np.repeat(ranks, N),
                "k": np.arange(0, N),
                "freq": freq_arr,
                "T": np.concatenate([np.array([0]), 1 / freq_arr[1:]]),
                "conf": conf,
            }
        )
    )
    df1.append(
        pd.DataFrame(
            {
                "t_start": time_b[0],
                "t_end": time_b[-1],
                "T_s": 1 / freq,
                "N": N,
                "ranks": ranks,
            },
            index=[k],
        )
    )
    df2.append(
        pd.DataFrame(
            {"b": bandwidth, "t": time_b, "ranks": np.repeat(ranks, len(time_b))}
        )
    )
    return df0, df1, df2, df3


def display_prediction(argv: list, prediction: dict) -> None:
    func_name = argv[0][argv[0].rfind("/") + 1 : -3]
    if "ftio" == func_name:
        CONSOLE.set(True)
        if prediction:
            freq, conf = get_dominant_and_conf(prediction)
            if not np.isnan(freq):
                CONSOLE.print(
                    f"[cyan underline]Predection results:[/]\n[cyan]Frequency:[/] {freq:.3e} Hz"
                    f"[cyan] ->[/] {np.round(1/freq,4)} s\n"
                    f"[cyan]Confidence:[/] {color_pred(conf)}"
                    f"{np.round(conf*100,2)}[/] %\n"
                )

if __name__ == "__main__":
    _ = main(sys.argv)
