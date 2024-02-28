from __future__ import annotations
import os
from sys import platform
from threading import Thread
import datetime
import json
import numpy as np
import pandas as pd
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import matplotlib
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.offline
import plotly.express as px
from plotly.subplots import make_subplots

from ftio.freq.freq_data import FreqData
from ftio.freq.helper import format_plot
from ftio.plot.units import set_unit
from ftio.freq.freq_html import create_html

# import plotly.io as pio

matplotlib.rcParams["backend"] = "TkAgg"


class FreqPlot:
    """For plotting the result of ftio"""

    def __init__(self, argv):
        self.render = "dynamic"
        self.plot_engine = "plotly"
        self.dtw = True
        self.dominant = []
        self.recon = False
        self.psd = False
        if not isinstance(argv, bool):
            D1 = []
            D2 = []
            D3 = []
            j = 0
            self.check = 0
            self.modes = ["async_write", "sync_write", "async_read", "sync_read"]
            self.s = []
            mode = "async_write"
            if isinstance(argv, list):
                if len(argv) <= 1:
                    self.paths = ["."]
                else:
                    self.paths = []
                    for i in range(1, len(argv)):
                        if "sync_" in str(argv[i]):
                            mode = str(argv[i])
                        elif "static" in str(argv[i]) or "dynamic" in str(argv[i]):
                            self.render = str(argv[i])
                        else:
                            self.paths.append(str(argv[i]))
            else:
                self.paths = [argv]

            print("\033[1;32m--------------------------------------------\n\033[1;32m")
            self.Print_info(argv[0])
            print("\n\033[1;35mPlot mode is %s\033[1;0m\n" % (mode))
            for path in self.paths:
                print(
                    "\n\033[1;34mLoading folder(%i,%i): %s\033[1;0m"
                    % (self.paths.index(path) + 1, len(self.paths), path)
                )
                # print ("\033[1;34m   "+'-'*len("Current folder(%i,%i): %s" % (self.paths.index(path) + 1, len(self.paths),path))+"\033[1;0m")
                if "DFT.json" not in path[-8:]:  # not single file
                    # path = path[:path.rfind("/")]
                    if path[-1] == "/":
                        path = path[:-1]
                    for root, _, files in os.walk(path):
                        for file in sorted(files, key=len):
                            if "DFT.json" in file[-8:]:
                                file = os.path.join(root, file)
                                print(" '-> Current file: " + file)
                                f = open(file)
                                data = json.load(f)
                                mode = self.Check_Mode(data, mode)
                                D1.append(pd.DataFrame(data=data.get(mode).get("data")))
                                D2.append(
                                    pd.DataFrame(
                                        data=data.get(mode).get("settings"), index=[j]
                                    )
                                )
                                D3.append(
                                    pd.DataFrame(data=data.get(mode).get("original"))
                                )
                                D1[j] = pd.concat(
                                    [
                                        D1[j],
                                        pd.DataFrame(
                                            {
                                                "ranks": [D2[j]["ranks"][j]]
                                                * D2[j]["N"][j],
                                                "k": [
                                                    x for x in range(0, D2[j]["N"][j])
                                                ],
                                                "freq": [
                                                    x
                                                    / (D2[j]["N"][j] * D2[j]["T_s"][j])
                                                    for x in range(0, D2[j]["N"][j])
                                                ],
                                                "T": [
                                                    (
                                                        (
                                                            D2[j]["N"][j]
                                                            * D2[j]["T_s"][j]
                                                        )
                                                        / x
                                                        if x > 0
                                                        else 0
                                                    )
                                                    for x in range(0, D2[j]["N"][j])
                                                ],
                                            }
                                        ),
                                    ],
                                    axis=1,
                                )
                                if "b" in D3[j]:
                                    D3[j] = pd.concat(
                                        [
                                            D3[j],
                                            pd.DataFrame(
                                                {
                                                    "ranks": [D2[j]["ranks"][j]]
                                                    * len(D3[j]["b"])
                                                }
                                            ),
                                        ],
                                        axis=1,
                                    )
                                j += 1
                        break  # no recusive walk
                else:
                    file = path
                    print("| -> Current file: " + file)
                    f = open(file)
                    data = json.load(f)
                    mode = self.Check_Mode(data, mode)
                    D1.append(pd.DataFrame(data=data.get(mode).get("data")))
                    D2.append(
                        pd.DataFrame(data=data.get(mode).get("settings"), index=[j])
                    )
                    D3.append(pd.DataFrame(data=data.get(mode).get("original")))
                    D1[j] = pd.concat(
                        [
                            D1[j],
                            pd.DataFrame(
                                {
                                    "ranks": [D2[j]["ranks"][j]] * D2[j]["N"][j],
                                    "k": [x for x in range(0, D2[j]["N"][j])],
                                    "freq": [
                                        x / (D2[j]["N"][j] * D2[j]["T_s"][j])
                                        for x in range(0, D2[j]["N"][j])
                                    ],
                                    "T": [
                                        (
                                            (D2[j]["N"][j] * D2[j]["T_s"][j]) / x
                                            if x > 0
                                            else 0
                                        )
                                        for x in range(0, D2[j]["N"][j])
                                    ],
                                }
                            ),
                        ],
                        axis=1,
                    )
                    if "b" in D3[j]:
                        D3[j] = pd.concat(
                            [
                                D3[j],
                                pd.DataFrame(
                                    {"ranks": [D2[j]["ranks"][j]] * len(D3[j]["b"])}
                                ),
                            ],
                            axis=1,
                        )
                    j += 1

            # print("--------------------------------------------\n")
            self.n = len(self.s)
            self.D = FreqData(
                pd.concat(D1, ignore_index=True),
                pd.concat(D2, ignore_index=True),
                pd.concat(D3, ignore_index=True),
            )

    def add_df(self, n, D1, D2, D3, D4=[]):
        self.n = n
        self.D = FreqData(
            pd.concat(D1, ignore_index=True),
            pd.concat(D2, ignore_index=True),
            pd.concat(D3, ignore_index=True),
        )
        if isinstance(D4, list) and D4:  # and not D4.empty:
            self.dominant = pd.concat(D4, ignore_index=True)

    def set(self, dict):
        for prop, value in dict.items():
            if prop in "render":
                self.render = value
            elif prop in "plot_engine":
                self.plot_engine = value
            elif prop in "dtw":
                self.dtw = value
            elif prop in "reconstruction":
                self.recon = value
            elif prop in "psd":
                self.psd = value

    def Check_Mode(self, data, mode):
        if self.check == 0:
            if not self.modes:
                print("no valid mode")
                exit(0)
            if not data.get(mode)["data"]:
                self.modes.remove(mode)
                mode = self.Check_Mode(data, self.modes[0])
            else:
                self.check = 1
                if len(self.modes) < 4:
                    print("\033[1;35mMode adjusted %s\033[1;0m" % (mode))
        return mode

    def Print_info(self, s):
        name = text[text.rfind("/") + 1 : -3].capitalize()
        console = Console()
        title = Panel(
            Text(name, justify="center"),
            style="bold white on cyan",
            border_style="white",
            title_align="left",
        )
        text = "\n[cyan]Author:[/] Ahmad Tarraf\n"
        text += f"[cyan]Date:[/]   {str(datetime.date.today())}\n"
        text += f"[cyan]Version:[/]   {1.0}\n"
        text += f"[cyan]License:[/]   --\n"
        # console.print(Panel(Group(title,text), style="white", border_style='blue'))
        console.print(title)
        console.print(text)

    def Plot(self):
        if "mat" not in self.plot_engine and "plotly" not in self.plot_engine:
            return

        # Settings
        console = Console()
        all_or_10 = False
        # template = "plotly_dark"
        # conf = {"toImageButtonOptions": {"format": "svg", "scale": 1}}
        conf = {"toImageButtonOptions": {"format": "png", "scale": 4}}
        template = "plotly"
        width = 1100
        height = 500  # 600
        font_settings = {
            "family": "Courier New, monospace",
            "size": 24,
            "color": "black",
        }
        colors = px.colors.qualitative.Plotly
        colors.pop(1)

        # Init
        top = []
        f = []
        bar_plot = go.Figure()
        color_counter = 0

        if "dark" in template:
            color_bar = "white"
        else:
            color_bar = "black"
        # https://plotly.com/python/renders/
        if self.render == "dynamic":
            # pio.renders.default = "browser"
            slider_cond = False
            visible = "legendonly"
        else:
            # pio.renders.default ="png"
            slider_cond = False
            visible = True
        console.print(
            f"\n[underline cyan]Ploting:[/]\n"
            f"[cyan]Plot render:[/] {self.render}\n"
            f"[cyan]Plot engine:[/] {self.plot_engine}\n"
            f"[cyan]DTW calculation:[/] {self.dtw}\n"
        )

        def Scatter(**kwargs):
            if self.render == "dynamic":
                return go.Scatter(kwargs)
            else:
                return go.Scattergl(kwargs)

        ranks = np.sort(pd.unique(self.D.settings_df["ranks"]))
        for r in ranks:
            index_set = self.D.settings_df["ranks"].isin([r])
            index_data = self.D.data_df["ranks"].isin([r])
            if not self.D.original_df.empty:
                index_original = self.D.original_df["ranks"].isin([r])
            samples = np.arange(0, self.D.settings_df["N"][index_set].values)
            amp = self.D.data_df[index_data]["A"]
            freq = self.D.data_df[index_data]["freq"]
            found = False

            # reconstruct time
            time = (
                self.D.settings_df[index_set]["t_start"].values
                + samples * self.D.settings_df[index_set]["T_s"].values
            )

            if self.plot_engine == "plotly":
                f.append(go.Figure())
            else:
                bar_plot = plt.figure(figsize=(10, 4))
                f1 = plt.figure(figsize=(10, 4))

            limit = (
                self.D.data_df[index_data].index.min()
                + self.D.settings_df[index_set]["N"].values / 2
            )
            if "conf" in self.D.data_df:
                sorted_ref = self.D.data_df[index_data].sort_values("conf")
                dominant = self.dominant[self.dominant["ranks"].isin([r])]["k"].values
                # dominant=[0,7,14, 21, 28, 35,42,49, 56]
                if all_or_10:
                    dominant = np.concatenate(
                        (dominant, self.D.settings_df[index_set]["N"][0] - dominant)
                    )
            else:
                sorted_ref = self.D.data_df[index_data].sort_values("A")
                dominant = sorted_ref.tail(3).index

            top_3 = sorted_ref.tail(7).index
            top_3 = top_3[top_3 < limit[0]]
            top.append(top_3[-2:-1][0])
            if not all_or_10:
                # top_x = self.D.data_df[index_data].sort_values('A').tail(20).index
                top_x = self.D.data_df[index_data].sort_values("A").tail(5).index
                top_x = top_x[top_x < limit[0]]

            name_dominant = ""
            # set the unit and order
            unit, order = set_unit(self.D.data_df[index_data]["b_sampled"])
            # unit = "MB/s" compatibility with old version
            for k in samples:
                x = (
                    (1 / len(samples))
                    * amp.values[k]
                    * np.cos(
                        2
                        * np.pi
                        * samples
                        * k
                        / (self.D.settings_df[index_set]["N"].values)
                        + self.D.data_df[index_data]["phi"].values[k]
                    )
                )
                if k == 0:
                    sum_all_components = x
                    sum_dominant = np.zeros(x.size)
                    # recon with DC offset
                    if self.recon:
                        sum_top_2 = x
                        sum_top_3 = x
                        sum_top_5 = x
                        sum_top_10 = x
                    dominant_X1 = x
                    dominant_X2 = x
                    dominant_k1 = top_3[-2]
                    dominant_k2 = top_3[-3]

                else:
                    sum_all_components = sum_all_components + x
                    if k in dominant:
                        sum_dominant = sum_dominant + x
                        found = True
                    if self.recon:
                        if k in sorted_ref.tail(3).index:
                            sum_top_2 = sum_top_2 + x
                        if k in sorted_ref.tail(5).index:
                            sum_top_3 = sum_top_3 + x
                        if k in sorted_ref.tail(9).index:
                            sum_top_5 = sum_top_5 + x
                        if k in sorted_ref.tail(19).index:
                            sum_top_10 = sum_top_10 + x

                    if k == dominant_k1:
                        dominant_X1 = (
                            dominant_X1 + 2 * x if not all_or_10 else dominant_X1 + x
                        )
                    if k == dominant_k2:
                        dominant_X2 = (
                            dominant_X2 + 2 * x if not all_or_10 else dominant_X2 + x
                        )

                length = len(samples)
                if "mat" in self.plot_engine:
                    if all_or_10:
                        s = "%.1e*cos(2\u03C0*%.1f*t%+.2f)" % (
                            order * amp.values[k] / length,
                            k,
                            self.D.data_df[index_data]["phi"].values[k],
                        )
                        plt.plot(time, x * order, linewidth=0.7, label="_nolegend_")
                    else:
                        if self.D.data_df[index_data].index[k] in top_x:
                            if k == 0 or k == len(samples) / 2:
                                a = 1
                            else:
                                a = 2

                            if round(freq.values[k], 2) > 0:
                                s = f"{a / length * order*amp.values[k]:.1e}*cos(2\u03C0*{freq.values[k]:.2f}*t+{self.D.data_df[index_data]['phi'].values[k]:.2f})"
                            else:
                                s = f"{a / length * order*amp.values[k]:.1e}*cos(2\u03C0*{freq.values[k]:.2e}*t+{self.D.data_df[index_data]['phi'].values[k]:.2e})"
                            plt.plot(time, a * x * order, linewidth=0.9, label=s)
                            # if (k in dominant ):
                            if k in dominant and k != 0:
                                if name_dominant:
                                    name_dominant = name_dominant + "\n+ " + s
                                else:
                                    name_dominant = s
                else:  # pltoly
                    if self.D.data_df[index_data].index[k] in top_x:
                        # plot only real
                        if k == 0 or k == len(samples) / 2:
                            a = 1
                        else:
                            a = 2
                        if round(freq.values[k], 1) > 0 and amp.values[k] < 100:
                            s = f"{a / length * order*amp.values[k]:.1f}*cos(2\u03C0*{freq.values[k]:.2f}*t{self.D.data_df[index_data]['phi'].values[k]:+.2f})"
                        else:
                            s = f"{a / length * order*amp.values[k]:.1e}*cos(2\u03C0*{freq.values[k]:.2e}*t{self.D.data_df[index_data]['phi'].values[k]:+.2f})"
                        ## For the paper
                        # s = f"{a / length * order*amp.values[k]:.0f}*cos(2\u03C0*{freq.values[k]:.2f}*t{self.D.data_df[index_data]['phi'].values[k]:+.2f})"
                        f[-1].add_trace(
                            Scatter(
                                x=time,
                                y=a * x * order,
                                mode="lines",
                                name=s,
                                hovertemplate="<b>Time</b>: %{x:.2f} s"
                                + "<br><b>Amplitude</b>: %{y}"
                                + "<br><b>T</b>: %{text} s",
                                text=len(samples)
                                * [f"{self.D.data_df[index_data]['T'].values[k]:.2f}"],
                                marker_color=(
                                    colors[color_counter]
                                    if color_counter != 1
                                    else "rgb(70,220,70)"
                                ),
                            )
                        )
                        color_counter += 1

                        if k in dominant and k != 0:
                            if name_dominant:
                                name_dominant = name_dominant + " + " + s
                            else:
                                name_dominant = s
                        # in reality it is k/N instead of t
                        # if (k == 0 or k == len(samples)/2):
                        #     s = "%.1ecos(2pi*%.2f*t%+.2f)" % (amp.values[k], freq.values[k], self.D.data_df[index_data]["phi"].values[k])
                        #     f[-1].add_trace(Scatter(x=time,y=x,mode='lines',name=s, hovertemplate ='<b>Time</b>: %{x:.2f} s'+ '<br><b>Amplitude</b>: %{y}'+'<br><b>T</b>: %{text} s',text = len(samples)*['%.2f'%(self.D.data_df[index_data]["T"].values[k])]))
                        # else:
                        #     s = "%.1ecos(2pi*%.2f*t%+.2f)" % (a*amp.values[k], freq.values[k], self.D.data_df[index_data]["phi"].values[k])
                        #     f[-1].add_trace(Scatter(x=time,y=a*x,mode='lines',name=s, hovertemplate ='<b>Time</b>: %{x:.2f} s'+ '<br><b>Amplitude</b>: %{y}'+'<br><b>T</b>: %{text} s',text = len(samples)*['%.2f'%(self.D.data_df[index_data]["T"].values[k])]))
            if self.dtw:
                threads = []
                print("    '-> \033[1;35mCalculating DTW\033[1;0m")
                threads.append(
                    Thread(
                        target=evaluate_dtw,
                        args=(
                            dominant_X1,
                            sum_all_components,
                            self.D.data_df.iloc[dominant_k1]["freq"],
                        ),
                    )
                )
                threads.append(
                    Thread(
                        target=evaluate_dtw,
                        args=(
                            dominant_X2,
                            sum_all_components,
                            self.D.data_df.iloc[dominant_k2]["freq"],
                        ),
                    )
                )
                # t.append(Thread(target=evaluate_dtw, args=(dominant_X3,sum,self.D.data_df.iloc[dominant_k3]['freq'])))
                for thread in threads:
                    thread.start()

            if "mat" in self.plot_engine:
                plt.plot(
                    time,
                    sum_all_components * order,
                    linestyle="-",
                    marker=".",
                    color="deepskyblue",
                    label="Reconstructed signal",
                )
                plt.xlim(time[0], time[-1])
                plt.ticklabel_format(axis="y", style="sci", scilimits=(-5, 3))
                plt.ticklabel_format(axis="x", style="sci", scilimits=(-5, 3))
                plt.xticks(fontsize=12)
                plt.yticks(fontsize=12)
                plt.ylabel(f"Bandwidth ({unit})", fontsize=17)
                plt.xlabel("Time (s)", fontsize=17)
                plt.grid(True)
                plt.legend(loc="upper left", ncol=2, fontsize=13)
                plt.tight_layout()
                f1.show()

                f2 = plt.figure(figsize=(10, 4))
                if not self.D.original_df.empty:
                    plt.fill_between(
                        self.D.original_df[index_original]["t"],
                        0,
                        self.D.original_df[index_original]["b"] * order,
                        label="Original signal",
                        alpha=0.5,
                        step="post",
                        color="royalblue",
                    )
                    plt.plot(
                        self.D.original_df[index_original]["t"],
                        self.D.original_df[index_original]["b"] * order,
                        drawstyle="steps-post",
                        color="royalblue",
                    )
                # plt.fill_between(time,0,sum,label="Reconstructed signal",alpha=0.5,step="post")
                # plt.plot(time,sum, drawstyle="steps-post")
                plt.fill_between(
                    time,
                    0,
                    self.D.data_df[index_data]["b_sampled"] * order,
                    label="Discrete signal",
                    alpha=0.6,
                    step="post",
                    color="red",
                )
                plt.plot(
                    time,
                    self.D.data_df[index_data]["b_sampled"] * order,
                    drawstyle="steps-post",
                    color="red",
                )
                if found:
                    plt.fill_between(
                        time,
                        0,
                        y2=sum_dominant * order,
                        label=name_dominant,
                        alpha=0.6,
                        step="post",
                        color="limegreen",
                    )
                    plt.plot(
                        time,
                        sum_dominant * order,
                        drawstyle="steps-post",
                        color="limegreen",
                    )
                if self.recon:
                    plt.fill_between(
                        time,
                        0,
                        y2=sum_top_2 * order,
                        label="Recon. top 2 signal",
                        alpha=0.6,
                        step="post",
                        color="gold",
                    )
                    plt.plot(
                        time, sum_top_2 * order, drawstyle="steps-post", color="gold"
                    )
                    plt.fill_between(
                        time,
                        0,
                        y2=sum_top_3 * order,
                        label="Recon. top 3 signal",
                        alpha=0.6,
                        step="post",
                        color="cyan",
                    )
                    plt.plot(
                        time, sum_top_3 * order, drawstyle="steps-post", color="cyan"
                    )
                    plt.fill_between(
                        time,
                        0,
                        y2=sum_top_5 * order,
                        label="Recon. top 5 signal",
                        alpha=0.6,
                        step="post",
                        color="purple",
                    )
                    plt.plot(
                        time, sum_top_5 * order, drawstyle="steps-post", color="purple"
                    )
                    plt.fill_between(
                        time,
                        0,
                        y2=sum_top_10 * order,
                        label="Recon. top 10 signal",
                        alpha=0.6,
                        step="post",
                        color="slategrey",
                    )
                    plt.plot(
                        time,
                        sum_top_10 * order,
                        drawstyle="steps-post",
                        color="slategrey",
                    )
                plt.xlim(time[0], time[-1])
                plt.ticklabel_format(axis="y", style="sci", scilimits=(-5, 3))
                plt.ticklabel_format(axis="x", style="sci", scilimits=(-5, 3))
                plt.xticks(fontsize=12)
                plt.yticks(fontsize=12)
                plt.ylabel(f"Bandwidth ({unit})", fontsize=17)
                plt.xlabel("Time (s)", fontsize=17)
                plt.grid(True)
                plt.legend(loc="upper left", ncol=1, fontsize=13)
                plt.tight_layout()
                f2.show()

                f3 = plt.figure(figsize=(10, 4))
                # settings
                full = False
                percent = True

                if not full:
                    n_samples = len(freq)
                    last = int(n_samples / 2) - 1
                    amp = 2 * amp[0 : last + 1]
                    amp[last] = amp[last] / 2
                    amp[0] = amp[0] / 2
                    freq = freq[0 : int(n_samples / 2)]

                mode = "Amplitude"
                if self.psd:
                    amp = amp * amp / len(amp)
                    mode = "Power"

                if percent:
                    mode = "Normed " + mode + " (%)"
                    amp = 100 * amp / amp.sum()

                plt.bar(
                    freq,
                    amp,
                    edgecolor="k",
                    width=freq[1] - freq[0],
                )
                plt.ticklabel_format(axis="y", style="sci", scilimits=(-5, 3))
                plt.ticklabel_format(axis="x", style="sci", scilimits=(-5, 3))
                plt.xticks(fontsize=12)
                plt.yticks(fontsize=12)
                plt.ylabel(mode, fontsize=17)
                plt.xlabel("Frequency (Hz)", fontsize=17)
                plt.grid(True)
                plt.legend(loc="upper left", ncol=2, fontsize=13)
                plt.tight_layout()
                f3.show()

            else:  # pltoly
                #! Reconstructed plot
                #!######################
                colors = px.colors.qualitative.Plotly

                f[-1].add_trace(
                    Scatter(
                        x=time,
                        y=sum_all_components * order,
                        mode="lines+markers",
                        name="Discrete signal",
                        line={"shape": "hv"},
                        marker_color="rgb(180,30,30)",
                    )
                )
                f[-1].update_layout(
                    xaxis_title="Time (s)",
                    yaxis_title=f"Bandwidth ({unit})",
                    width=width,
                    height=height / 1.1,
                    template=template,
                )
                f[-1].update_layout(
                    legend=dict(
                        orientation="h", yanchor="top", y=0.99, xanchor="left", x=0.01
                    )
                )
                # f[-1].update_layout(legend=dict(orientation="h", yanchor="bottom",y=1.02, xanchor="right", x=1))
                f[-1].update_xaxes(range=[time[0], time[-1]])
                f[-1] = format_plot(f[-1])
                f[-1].show(config=conf)

                f.append(go.Figure())
                fill = "tozeroy"
                # if len(time) > 1e3:
                #     fill = None
                #     print ('too many points, removing fill')

                #! Dominant plot
                #!######################
                if not self.D.original_df.empty and (self.render == "dynamic" or  len(time) < 1e3):
                    f[-1].add_trace(
                        Scatter(
                            x=self.D.original_df[index_original]["t"],
                            y=self.D.original_df[index_original]["b"] * order,
                            mode="lines+markers",
                            name="Original signal",
                            fill=fill,
                            line={"shape": "hv"},
                            marker_color="rgb(0,150,250)",
                        )
                    )
                else:
                    console.print(
                        "[orange]Too many data points for original signal[/]\n"
                        "[orange]>> skipping plotting it[/]\n"
                        "[orange]>> use ftio ... -e mat to show this plot or set ftio ... -re static[/]\n"
                    )
                # f[-1].add_trace(Scatter(x=time,y=sum,mode='lines+markers',name="Reconstructed signal",fill=fill, line={"shape": 'hv'},visible=visible))
                f[-1].add_trace(
                    Scatter(
                        x=time,
                        y=self.D.data_df[index_data]["b_sampled"] * order,
                        mode="lines+markers",
                        name="Discrete signal",
                        fill=fill,
                        line={"shape": "hv"},
                        marker_color="rgb(180,30,30)",
                    )
                )
                if found:
                    if r > 1000:
                        fill = None
                    f[-1].add_trace(
                        Scatter(
                            x=time,
                            y=sum_dominant * order,
                            mode="lines+markers",
                            name=name_dominant,
                            fill=fill,
                            line={"shape": "hv"},
                            marker_color="rgb(70,220,70)",
                        )
                    )
                if self.recon:
                    f[-1].add_trace(
                        Scatter(
                            x=time,
                            y=sum_top_2 * order,
                            mode="lines+markers",
                            name="Recon. top 2 signal",
                            fill=fill,
                            line={"shape": "hv"},
                            visible="legendonly",
                        )
                    )
                    f[-1].add_trace(
                        Scatter(
                            x=time,
                            y=sum_top_3 * order,
                            mode="lines+markers",
                            name="Recon. top 3 signal",
                            fill=fill,
                            line={"shape": "hv"},
                            visible="legendonly",
                        )
                    )
                    f[-1].add_trace(
                        Scatter(
                            x=time,
                            y=sum_top_5 * order,
                            mode="lines+markers",
                            name="Recon. top 5 signal",
                            fill=fill,
                            line={"shape": "hv"},
                            visible="legendonly",
                        )
                    )
                    f[-1].add_trace(
                        Scatter(
                            x=time,
                            y=sum_top_10 * order,
                            mode="lines+markers",
                            name="Recon. top 10 signal",
                            fill=fill,
                            line={"shape": "hv"},
                            visible="legendonly",
                        )
                    )
                rangeslider(
                    f[-1],
                    time,
                    2 / self.D.data_df.iloc[dominant_k1]["freq"],
                    slider_cond,
                )
                f[-1].update_layout(
                    xaxis_title="Time (s)",
                    yaxis_title=f"Bandwidth ({unit})",
                    font=font_settings,
                    # width=1.05*width,
                    width=width,
                    height=height / 1.1,
                    # title="Time Plot (Ranks %i)" % r,
                    template=template,
                )
                f[-1].update_layout(
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                    # legend=dict(yanchor="top", y=0.99, xanchor="right", x=.99)
                )

                f[-1].update_xaxes(range=[time[0], time[-1]])
                if isinstance(sum_dominant, list):
                    f[-1].update_yaxes(
                        range=[
                            min(sum_dominant),
                            1.2 * self.D.original_df[index_original]["b"].max(),
                        ]
                    )
                # f[-1].update_yaxes(range=[-2000, 72000])
                f[-1] = format_plot(f[-1])
                # f[-1].show(config=conf)

                #! Frequency spectrum
                #!######################
                fig_tmp = plot_one_spectrum(self.psd, freq, amp, False, True)
                fig_tmp.update_layout(
                    font=font_settings,
                    width=width,
                    height=height / 1.3,
                    coloraxis_colorbar=dict(
                        yanchor="top", y=1, x=1, ticks="outside", title=""
                    ),
                    template=template,
                    # title="Spectrum (Ranks %i)" % r
                )
                # fig_tmp.show(config=conf)
                f.append(fig_tmp)

            if self.dtw:
                for thread in threads:
                    thread.join()

            # f.append(go.Figure())
            # f[-1].add_trace(go.Bar(x=samples,y=amp,marker_color='rgb(26, 118, 255)',marker_line=dict(width=1, color=color_bar), hovertemplate ='<br><b>k</b>: %{x}<br>' + '<b>Amplitude</b>: %{y:.2e}' +'<br><b>Frequency</b>: %{text} Hz<br>',text = ['%.2f'%i for i in freq]))
            # rangeslider(f[-1],samples,int(len(samples)/5),len(samples) > 1e3 and True)
            # f[-1].update_layout(xaxis_title='Frequency bins', yaxis_title='Amplitude',font=font_settings, width=width, height=height, title = 'Frequency Plot (Ranks %i)'%r, coloraxis_colorbar=dict(yanchor="top", y=1, x=0,ticks="outside"), template = template)

            if "plotly" == self.plot_engine:
                fig_tmp = plot_one_spectrum(self.psd, freq, amp, True)
                fig_tmp.update_traces(marker_line=dict(width=0.1, color=color_bar))
                fig_tmp.update_layout(
                    font=font_settings,
                    width=width,
                    height=height / 1.3,
                    # title="Full Spectrum (Ranks %i)" % r,
                    coloraxis_colorbar=dict(
                        yanchor="top", y=1, x=1, ticks="outside", title=""
                    ),
                    template=template,
                )
                f.append(fig_tmp)
                rangeslider(
                    f[-1],
                    freq,
                    freq[int(len(freq) / 5)],
                    len(samples) > 1e3 and slider_cond,
                )

                # bar_plot.update_layout(barmode="group", template=template)
                # bar_plot.add_trace(
                #     go.Bar(
                #         x=samples,
                #         y=amp,
                #         textposition="inside",
                #         textangle=0,
                #         name=("Ranks %i") % r,
                #         hovertemplate="<br><b>Frequency</b>: %{x} Hz<br>"
                #         + "<b>Amplitude</b>: %{y:.2e}"
                #         + "<br><b>T</b>: %{text} s<br>",
                #         text=["%.2f" % i for i in self.D.data_df[index_data]["T"]],
                #     )
                # )
                # bar_plot.update_layout(
                #     xaxis_title="Frequency bins",
                #     yaxis_title="Amplitude",
                #     width=width,
                #     height=height,
                #     title="Frequency Plot",
                #     font=font_settings,
                #     barmode="group",
                # )

            #! 3d plot
            # prediction_plot.add_traces(list(px.scatter_3d(self.D.data_df.iloc[top_3], x='A', y='ranks', z='k' ,color='T', symbol='ranks',opacity=0.7,hover_data={'ranks':True, 'k'  :True, 'A':':.2f', 'F': (':.2f (Hz)',self.D.data_df.iloc[top_3]['freq']), 'T': ':.2f (s)'}).select_traces()))

        if "plotly" == self.plot_engine:
            # bar_plot.update_xaxes(range=[0, 100])
            # f.append(bar_plot)

            #! 3d plot
            # prediction_plot.update_layout(template = template,margin=dict(l=0, r=0, b=0, t=0), width=width, height = height, title = 'Frequency Prediction', font=font_settings, coloraxis_colorbar=dict(title='Perodicity (s)', yanchor="top", y=1, x=0,ticks="outside"),scene = dict(xaxis_title='Amplitude',yaxis_title='Ranks',zaxis_title='Frequency (Hz)',xaxis=dict(showgrid=True, gridwidth=1, gridcolor='gray'),yaxis=dict(showgrid=True, gridwidth=1, gridcolor='gray'),zaxis=dict(showgrid=True, gridwidth=1, gridcolor='gray')))
            # prediction_plot.layout.scene.aspectratio = {'x':2, 'y':1, 'conf':1}
            # f.append(prediction_plot)

            # fig_tmp = px.scatter_3d(self.D.data_df, x='k', y='ranks', z='A',color='A', symbol='ranks', opacity=0.7)
            # tight layout
            # fig_tmp.update_layout(
            # template = template,
            # margin=dict(l=0, r=0, b=0, t=0), width=width, height = height, title = 'Frequency Plot',
            # font=font_settings,
            # coloraxis_colorbar=dict(title='Frequency (Hz)', yanchor="top", y=1, x=0, ticks="outside"),
            # scene = dict(xaxis_title='Frequency (Hz)',yaxis_title='Ranks', zaxis_title='Bandwidth (B/s)',
            # xaxis=dict(showgrid=True, gridwidth=1, gridcolor='gray'),
            # yaxis=dict(showgrid=True, gridwidth=1, gridcolor='gray'),
            # zaxis=dict(showgrid=True, gridwidth=1, gridcolor='gray')))
            # fig_tmp.layout.scene.aspectratio = {'x':2, 'y':1, 'conf':1}
            # f.append(fig_tmp)

            # f.append(go.Figure())
            # f[-1].add_traces(
            #     list(
            #         px.line(
            #             self.D.data_df.iloc[top],
            #             x="ranks",
            #             y="T",
            #             color="k",
            #             markers=True,
            #             hover_data={
            #                 "ranks": True,
            #                 "k": True,
            #                 "A": ":.2f",
            #                 "F": (":.2f (Hz)", self.D.data_df.iloc[top]["freq"]),
            #                 "T": True,
            #             },
            #         ).select_traces()
            #     )
            # )
            # f[-1].update_layout(
            #     xaxis_title="Ranks",
            #     yaxis_title="Period (s)",
            #     font=font_settings,
            #     width=width,
            #     height=height,
            #     title="Prediction",
            #     template=template,
            # )
            create_html(f, self.render, conf, "freq")
        else:
            input()


##Fill DTW Matrix
def fill_dtw_cost_matrix(s1, s2):
    l_s_1, l_s_2 = len(s1), len(s2)
    cost_matrix = np.zeros((l_s_1 + 1, l_s_2 + 1))
    for i in range(l_s_1 + 1):
        for j in range(l_s_2 + 1):
            cost_matrix[i, j] = np.inf
    cost_matrix[0, 0] = 0

    for i in range(1, l_s_1 + 1):
        for j in range(1, l_s_2 + 1):
            cost = abs(s1[i - 1] - s2[j - 1])
            # take last min from the window
            prev_min = np.min(
                [
                    cost_matrix[i - 1, j],
                    cost_matrix[i, j - 1],
                    cost_matrix[i - 1, j - 1],
                ]
            )
            cost_matrix[i, j] = cost + prev_min

    return cost_matrix[-1, -1]


##Call DTW function


def fdtw(s1, s2):
    distance, path = fastdtw(s1, s2, dist=euclidean)
    return distance, path


def rangeslider(f, arr, limit, cond="", point_limit=2.5e3):
    if isinstance(cond, str):
        cond = len(arr) > point_limit
    try:
        if cond:
            if limit < arr[-1]:
                myrange = [arr[0], limit]
                f.update_layout(
                    xaxis=dict(
                        rangeselector=dict(
                            buttons=[
                                dict(
                                    count=2,
                                    label="phase",
                                    step="month",
                                    stepmode="backward",
                                ),
                                dict(label="all", step="all"),
                            ]
                        ),
                        rangeslider=dict(visible=True, range=[arr[0], arr[-1]]),
                        type="linear",
                        range=myrange,
                    )
                )  # change type to date to show buttons
            else:
                pass
        else:
            pass
    except:
        try:
            myrange = [arr[0], arr[int(len(arr) / 5)]]
            f.update_layout(
                xaxis=dict(
                    rangeselector=dict(
                        buttons=[
                            dict(
                                count=2,
                                label="phase",
                                step="month",
                                stepmode="backward",
                            ),
                            dict(label="all", step="all"),
                        ]
                    ),
                    rangeslider=dict(visible=True, range=[arr[0], arr[len(arr) - 1]]),
                    type="linear",
                    range=myrange,
                )
            )  # change type to date to show buttons
        except:
            pass


def evaluate_dtw(discret_arr, original_discret_signal, freq):
    dtw_k1, _ = fastdtw(discret_arr, original_discret_signal, dist=euclidean)
    print("    '-> \033[1;32mfreq %.2f Hz\033[1;0m --> dtw: %d" % (freq, dtw_k1))


def plot_spectrum(
    amp: np.ndarray, freq: np.ndarray, mode: str = "Amplitude", percent: bool = False
):
    template = "plotly"
    name = "Amplitude" if "amp" in mode.lower() else "Power"
    unit = ""
    if percent:
        name = "Normed " + name
        unit = unit + " (%)"
        amp = 100 * amp / amp.sum()

    df_tmp = pd.DataFrame(
        data={
            "A": amp,
            "freq": freq,
        }
    )
    # fig_tmp = px.bar(df_tmp, x="freq", y="A", color="A", color_continuous_scale='Bluered')
    # fig_tmp = px.bar(df_tmp, x="freq", y="A", color="A", color_continuous_scale=["rgb(0,10,130)", "rgb(130,30,130)", "rgb(255,50,50)"])
    # fig_tmp = px.bar(df_tmp, x="freq", y="A", color="A", color_continuous_scale="plasma")
    # cyan - purple
    # fig_tmp = px.bar(df_tmp, x="freq", y="A", color="A", color_continuous_scale=[ "rgb(90, 40, 90)", "rgb(113, 221, 255)" ])
    fig_tmp = px.bar(
        df_tmp,
        x="freq",
        y="A",
        color="A",
        color_continuous_scale=["rgb(0,50,150)", "rgb(150,50,150)", "rgb(255,50,0)"],
    )

    fig_tmp.update_traces(
        marker_line=dict(width=0.2, color="black"),
        hovertemplate="<b>Frequency</b>: %{x:.2e} Hz <br><b>"
        + f"{name}"
        + "</b>: %{y:.2e}"
        + f"{unit}",
    )
    fig_tmp.update_layout(
        xaxis_title="Frequency (Hz)",
        yaxis_title=name + unit,
        coloraxis_colorbar=dict(yanchor="top", y=1, x=0, ticks="outside"),
        template=template,
    )
    fig_tmp = format_plot(fig_tmp)
    return fig_tmp, name + unit


def plot_both_spectrums(args, freq: np.ndarray, amp: np.ndarray, full: bool = True):
    fig_1 = make_subplots(
        rows=2,
        cols=2,
        specs=[[{"colspan": 2}, None], [{"colspan": 2}, None]],
    )

    start = 1

    if not full:
        indecies = np.arange(start, int(len(amp) / 2) + 1)
        freq = freq[indecies]
        amp = 2 * amp[indecies]
        amp[-1] = amp[-1] / 2
        if start == 0:
            amp[0] = amp[0] / 2

    if args.psd:
        power = amp
        amplitude = np.sqrt(amp) * len(amp)
    else:
        power = amp * amp / len(amp)
        amplitude = amp

    fig_tmp, name_plt = plot_spectrum(amplitude, freq, "Amplitude", False)
    layout = fig_tmp.layout
    for trace in list(fig_tmp.select_traces()):
        trace.update(marker={"coloraxis": "coloraxis"})
        fig_1.append_trace(trace, row=1, col=1)
    fig_tmp, name_plt1 = plot_spectrum(power, freq, "Power", True)
    for trace in list(fig_tmp.select_traces()):
        trace.update(marker={"coloraxis": "coloraxis2"})
        fig_1.append_trace(trace, row=2, col=1)
    fig_1.update_layout(layout)
    fig_1.update_layout(
        coloraxis={
            "colorbar": {
                "x": 1,
                "len": 0.4,
                "y": 0.8,
            },
        },
        coloraxis2={
            "colorbar": {
                "x": 1,
                "len": 0.4,
                "y": 0.2,
            },
        },
    )

    return fig_1, [name_plt, name_plt1]


def plot_one_spectrum(
    psd_flag: bool,
    freq: np.ndarray,
    amp: np.ndarray,
    full: bool = True,
    percent: bool = False,
) -> go.Figure:
    if not full:
        n_samples = len(freq)
        last = int(n_samples / 2) - 1
        amp = 2 * amp[0 : last + 1]
        amp[last] = amp[last] / 2
        amp[0] = amp[0] / 2
        freq = freq[0 : int(n_samples / 2)]

    if psd_flag:
        amp = amp * amp / len(amp)
        mode = "Power"
    else:
        mode = "Amplitude"

    fig_tmp, _ = plot_spectrum(amp, freq, mode, percent)
    return fig_tmp


def convert_and_plot(data, dfs: list, args) -> None:
    """convert from ftio and plot

    Args:
        data (_type_): _description_
        dfs (list): _description_
        args (argparse): _description_
    """
    freq_plot = FreqPlot(True)
    if any(x in args.engine for x in ["mat", "plot"]):
        freq_plot.add_df(len(data), dfs[0], dfs[1], dfs[2], dfs[3])
    freq_plot.set(
        {
            "render": args.render,
            "engine": args.engine,
            "dtw": args.dtw,
            "recon": args.reconstruction,
            "psd": args.psd,
        }
    )
    freq_plot.Plot()
