import numpy as np
import pandas as pd
from ftio.prediction.unify_predictions import  color_pred
from ftio.prediction.helper import get_dominant_and_conf
import matplotlib.pyplot as plt
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()


#!################
#! DFT flavors
#!################

# Wrapper 
def dft(b):
    return numpy_dft(b)


#1) Custome implementation
def dft_fast(b):
    N = len(b)
    X = np.repeat(complex(0, 0), N)  # np.zeros(N)
    for k in range(0, N):
        for n in range(0, N):
            X[k] = X[k] + b[n] * np.exp((-2 * np.pi * n * k / N) * 1j)
    return X

#2) numpy DFT
def numpy_dft(b):
    return np.fft.fft(b)

#3) DFT with complex
def dft_slow(b):
    N = len(b)
    n = np.arange(N)
    k = n.reshape((N, 1))
    e = np.exp(-2j * np.pi * k * n / N)
    X = np.dot(e, b)
    return X



def precision_dft(
    amp: np.ndarray, phi:np.ndarray, dominant_index:np.ndarray, b_sampled:np.ndarray, t_disc:np.ndarray, freq_arr:np.ndarray, plt_engine:str
) -> str:
    """calculates the precision of the dft

    Args:
        amp (np.ndarray): amplitude array from DFT
        phi (np.ndarray): phase array from DFT
        dominant_index (np.ndarray): index/indecies of dominant frequency/frequencies
        b_sampled (np.ndarray): discretized bandwdith
        t_disc (np.ndarray): discretized time (constant step size). Start at t_0
        freq_arr (np.ndarray): frequency array 
        plt_engine (str): comand line specific plot engine

    Returns:
        str: precision 
    """
    # 
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
        text += f"Precision of [cyan]{freq_arr[index]:.2f}[/] Hz is [cyan]{float(np.sum(x)) / total * 100:.2f}% [/]"
        text += f"(Positive only: [cyan]{float(np.sum(x_2)) / total * 100:.2f}%[/])\n"

        if showplot and ("mat" in plt_engine or "plotly" in plt_engine):
            plt.plot(t_disc, x, label=f"f = {freq_arr[index]:.2f} Hz")

    if showplot and ("mat" in plt_engine or "plotly" in plt_engine):
        plt.plot(t_disc, b_sampled, label="b_sampled")
        plt.ticklabel_format(axis="y", style="sci", scilimits=(-5, 3))
        plt.ticklabel_format(axis="x", style="sci", scilimits=(-5, 3))
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        plt.ylabel("Amplitude (B/s)", fontsize=17)
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
    func_name = argv[0][argv[0].rfind("/") + 1:]
    if "ftio" in func_name:
        if prediction:
            freq, conf = get_dominant_and_conf(prediction)
            if not np.isnan(freq):
                CONSOLE.info(
                    f"[cyan underline]Prediction results:[/]\n[cyan]Frequency:[/] {freq:.3e} Hz"
                    f"[cyan] ->[/] {np.round(1/freq,4)} s\n"
                    f"[cyan]Confidence:[/] {color_pred(conf)}"
                    f"{np.round(conf*100,2)}[/] %\n"
                )
            else:
                CONSOLE.info(
                        "[cyan underline]Prediction results:[/]\n"
                        "[red]No dominant frequency found[/]\n"
                    )

