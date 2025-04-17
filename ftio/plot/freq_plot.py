from __future__ import annotations
import os

import datetime
import json
import numpy as np
import pandas as pd
from argparse import Namespace
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import matplotlib
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

from ftio.freq.dtw import threaded_dtw
from ftio.freq.freq_data import FreqData
from ftio.plot.helper import format_plot
from ftio.plot.spectrum import plot_one_spectrum
from ftio.plot.units import set_unit
from ftio.freq.freq_html import create_html

# import plotly.io as pio

matplotlib.rcParams["backend"] = "TkAgg"


class FreqPlot:
    """For plotting the result of ftio"""

    def __init__(self, argv):
        self.render = "dynamic"
        self.plot_engine = "plotly"
        self.transform = "dft"
        self.dtw = True
        self.dominant = []
        self.recon = []
        self.psd = False
        self.name = ""
        if not isinstance(argv, bool):
            D1 = []
            D2 = []
            D3 = []
            j = 0
            self.check = 0
            self.modes = ["write_async", "write_sync", "read_async", "read_sync"]
            self.s = []
            mode = "write_async"
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

            print(
                "\033[1;32m--------------------------------------------\n\033[1;32m")
            self.print_info(argv[0])
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
                                mode = self.check_mode(data, mode)
                                D1.append(pd.DataFrame(
                                    data=data.get(mode).get("data")))
                                D2.append(
                                    pd.DataFrame(
                                        data=data.get(mode).get("settings"), index=[j]
                                    )
                                )
                                D3.append(
                                    pd.DataFrame(data=data.get(
                                        mode).get("original"))
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
                    mode = self.check_mode(data, mode)
                    D1.append(pd.DataFrame(data=data.get(mode).get("data")))
                    D2.append(
                        pd.DataFrame(data=data.get(
                            mode).get("settings"), index=[j])
                    )
                    D3.append(pd.DataFrame(
                        data=data.get(mode).get("original")))
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
                                    {"ranks": [D2[j]["ranks"][j]]
                                        * len(D3[j]["b"])}
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
            elif prop in "transform":
                self.transform = value
            elif prop in "name":
                self.name = value

    def check_mode(self, data, mode):
        if self.check == 0:
            if not self.modes:
                print("no valid mode")
                exit(0)
            if not data.get(mode)["data"]:
                self.modes.remove(mode)
                mode = self.check_mode(data, self.modes[0])
            else:
                self.check = 1
                if len(self.modes) < 4:
                    print("\033[1;35mMode adjusted %s\033[1;0m" % (mode))
        return mode

    def print_info(self, text: str) -> None:
        name = text[text.rfind("/") + 1: -3].capitalize()
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

    def plot(self):
        if "mat" not in self.plot_engine and "plotly" not in self.plot_engine:
            return

        # Settings
        # conf = {"toImageButtonOptions": {"format": "svg", "scale": 1}}
        conf = {"toImageButtonOptions": {"format": "png", "scale": 4}}
        width = 1100
        height = 500  # 600
        font_settings = {
            "family": "Courier New, monospace",
            "size": 24,
            "color": "black",
        }
        colors = px.colors.qualitative.Plotly
        colors.pop(1)
        f = []
        

        ranks = np.sort(pd.unique(self.D.settings_df["ranks"]))
        if self.transform == "dft":
            f = self.plot_dft(f, ranks, width,height, font_settings, conf,colors)
        else:
            pass

        if "plotly" in self.plot_engine:
            create_html(f, self.render, conf, self.name)
        else:
            input()


    def plot_dft(self,f,ranks,width, height, font_settings, conf, colors):
        # settings
        # Init
        top = []
        console = Console()
        f = []
        bar_plot = go.Figure()
        color_counter = 0
        template = "plotly"

        paper = True
        if "no_paper" in self.plot_engine:
            paper = False
        # template = "plotly_dark"
        
        # For faster scatteer plot
        def Scatter(**kwargs):
            if self.render == "dynamic":
                return go.Scatter(kwargs)
            else:
                return go.Scattergl(kwargs)

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
        all_or_10 = False
        sum_top = {}
        
        for r in ranks:
            index_set = self.D.settings_df["ranks"].isin([r])
            index_data = self.D.data_df["ranks"].isin([r])
            if not self.D.original_df.empty:
                index_original = self.D.original_df["ranks"].isin([r])

            samples = np.arange(0, self.D.settings_df["N"][index_set].values)
            amp = np.array(self.D.data_df[index_data]["A"])
            freq = np.array(self.D.data_df[index_data]["freq"])
            phi = np.array(self.D.data_df[index_data]["phi"])
            found = False

            # reconstruct time
            time = (
                self.D.settings_df[index_set]["t_start"].values
                + samples * self.D.settings_df[index_set]["T_s"].values
            )

            if  "plotly" in  self.plot_engine:
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
                    dominant = np.concatenate((dominant,self.D.settings_df[index_set]["N"][0] - dominant))
            else:
                sorted_ref = self.D.data_df[index_data].sort_values("A")
                dominant = sorted_ref.tail(3).index

            top_3 = sorted_ref.tail(7).index
            top_3 = top_3[top_3 < limit[0]]
            top.append(top_3[-2:-1][0])
            if not all_or_10:
                # top_x = self.D.data_df[index_data].sort_values('A').tail(20).index
                top_x = self.D.data_df[index_data].sort_values(
                    "A").tail(5).index
                top_x = top_x[top_x < limit[0]]

            name_dominant = ""
            # set the unit and order
            unit, order = set_unit(self.D.data_df[index_data]["b_sampled"])
            #
            # unit, order = set_unit(self.D.data_df[index_data]["b_sampled"]*1000) #compatibility with old version (For BWLIMIT)
            for k in samples:
                x = (
                    (1 / len(samples))
                    * amp[k]
                    * np.cos(
                        2
                        * np.pi
                        * samples
                        * k
                        / (self.D.settings_df[index_set]["N"].values)
                        + phi[k]
                    )
                )
                if k == 0:
                    sum_all_components = x
                    sum_dominant = np.zeros(x.size)
                    # recon with DC offset
                    if self.recon:
                        for top_index in self.recon:
                            sum_top[top_index] =  np.zeros_like(x)
                            sum_top[top_index] +=  x
                            
                    
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
                        for top_index in self.recon:
                            if k in sorted_ref.tail(1 + (top_index-1)*2).index:
                                sum_top[top_index] += x

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
                            order * amp[k] / length,
                            k,
                            phi[k],
                        )
                        plt.plot(time, x * order, linewidth=0.7,label="_nolegend_")
                    else:
                        if self.D.data_df[index_data].index[k] in top_x:
                            if k == 0 or k == len(samples) / 2:
                                a = 1
                            else:
                                a = 2

                            if round(freq[k], 2) > 0:
                                s = f"{a / length * order*amp[k]:.1e}*cos(2\u03C0*{freq[k]:.2f}*t+{phi[k]:.2f})"
                            else:
                                s = f"{a / length * order*amp[k]:.1e}*cos(2\u03C0*{freq[k]:.2e}*t+{phi[k]:.2e})"
                            plt.plot(time, a * x * order,linewidth=0.9, label=s)
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
                        if round(freq[k], 1) > 0 and amp[k] < 100:
                            s = f"{a / length * order*amp[k]:.1f}*cos(2\u03C0*{freq[k]:.2f}*t{self.D.data_df[index_data]['phi'].values[k]:+.2f})"
                        else:
                            s = f"{a / length * order*amp[k]:.1e}*cos(2\u03C0*{freq[k]:.2e}*t{self.D.data_df[index_data]['phi'].values[k]:+.2f})"
                        # For the paper
                        # s = f"{a / length * order*amp[k]:.0f}*cos(2\u03C0*{freq[k]:.2f}*t{self.D.data_df[index_data]['phi'].values[k]:+.2f})"
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
                        #     s = "%.1ecos(2pi*%.2f*t%+.2f)" % (amp[k], freq[k], self.D.data_df[index_data]["phi"].values[k])
                        #     f[-1].add_trace(Scatter(x=time,y=x,mode='lines',name=s, hovertemplate ='<b>Time</b>: %{x:.2f} s'+ '<br><b>Amplitude</b>: %{y}'+'<br><b>T</b>: %{text} s',text = len(samples)*['%.2f'%(self.D.data_df[index_data]["T"].values[k])]))
                        # else:
                        #     s = "%.1ecos(2pi*%.2f*t%+.2f)" % (a*amp[k], freq[k], self.D.data_df[index_data]["phi"].values[k])
                        #     f[-1].add_trace(Scatter(x=time,y=a*x,mode='lines',name=s, hovertemplate ='<b>Time</b>: %{x:.2f} s'+ '<br><b>Amplitude</b>: %{y}'+'<br><b>T</b>: %{text} s',text = len(samples)*['%.2f'%(self.D.data_df[index_data]["T"].values[k])]))
            if self.dtw:
                threads = threaded_dtw(
                    sum_all_components,
                    self.D.data_df,
                    dominant_X1,
                    dominant_k1,
                    dominant_X2,
                    dominant_k2,
                )

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
                    label="Sampled signal",
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
                colors = [
                    "gold", "cyan", "purple", "slategrey", "darkorange", "green", 
                    "blue", "red", "magenta", "brown", "pink", "yellowgreen", 
                    "lightblue", "indigo", "teal", "orchid", "crimson"
                ]

                if self.recon:
                    for i, top_index in enumerate(self.recon):
                        color = colors[i % len(colors)]  # Cycles through the colors list

                        # Fill the area between the curve and the x-axis
                        plt.fill_between(
                            time,
                            0,
                            y2=sum_top[top_index] * order,
                            label=f"Recon. top {top_index} signal",
                            alpha=0.6,
                            step="post",
                            color=color,
                        )
                        
                        # Plot the line on top of the fill
                        plt.plot(
                            time, sum_top[top_index] * order, drawstyle="steps-post", color=color
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
                    amp = 2 * amp[0: last + 1]
                    amp[last] = amp[last] / 2
                    amp[0] = amp[0] / 2
                    freq = freq[0: int(n_samples / 2)]

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
                        name="Sampled signal",
                        line={"shape": "hv"},
                        marker_color="rgb(180,30,30)",
                    )
                )
                f[-1].update_layout(
                    xaxis_title="Time (s)",
                    yaxis_title=f"Bandwidth ({unit})",
                    width=width if paper else 1.5*width,
                    height=height / 1.1,
                    template=template,
                )

                if paper:
                    f[-1].update_layout(
                        legend=dict(
                            orientation="h", yanchor="top", y=0.99, xanchor="left", x=0.01
                        )
                    )
                # else:
                #     f[-1].update_layout(legend=dict(orientation="h", yanchor="bottom",y=1.02, xanchor="right", x=1))
                    
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
                if not self.D.original_df.empty and (
                    self.render == "dynamic" or len(time) < 1e3
                ):
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
                        name="Sampled signal",
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
                    for top_index in self.recon:
                        f[-1].add_trace(
                            trace=Scatter(
                                x=time,
                                y=sum_top[top_index] * order,
                                mode="lines+markers",
                                name=f"Recon. top {top_index} signal",
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
                    width=width if paper else 1.5*width,
                    height=height / 1.1,
                    # title="Time Plot (Ranks %i)" % r,
                    template=template,
                )
                if paper:
                    f[-1].update_layout(
                        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                    )
                # else:
                #     f[-1].update_layout(
                #         legend=dict(yanchor="top", y=0.99, xanchor="right", x=.99)
                #     )

                f[-1].update_xaxes(range=[time[0], time[-1]])
                if isinstance(sum_dominant, list):
                    f[-1].update_yaxes(
                        range=[
                            min(sum_dominant),
                            1.2 *
                            self.D.original_df[index_original]["b"].max(),
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
            if "plotly" in self.plot_engine:
                    fig_tmp = plot_one_spectrum(self.psd, freq, amp, True)
                    fig_tmp.update_traces(
                        marker_line=dict(width=0.1, color=color_bar))
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
        return f


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
                        rangeslider=dict(visible=True, range=[
                                         arr[0], arr[-1]]),
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
                    rangeslider=dict(visible=True, range=[
                                     arr[0], arr[len(arr) - 1]]),
                    type="linear",
                    range=myrange,
                )
            )  # change type to date to show buttons
        except:
            pass



def convert_and_plot(args:Namespace, dfs: list, n:int = 1 ) -> None:
    """Convert data from ftio and plot the results.

    Args:
        args (Namespace): Command line arguments.
        dfs (list): List of dataframes containing the data to plot.
        n (int, optional): Number of dataframes. Defaults to 1.
    """
    freq_plot = FreqPlot(True)
    if any(x in args.engine for x in ["mat", "plot"]):
        freq_plot.add_df(n, dfs[0], dfs[1], dfs[2], dfs[3])

    if "plot_name" not in args:
        args.plot_name = "ftio_dft_result"


    if args.reconstruction:
        args.reconstruction = [int(x) for val in args.reconstruction for x in val.split(',')]

    if args.n_freq:
        if args.reconstruction and args.n_freq not in args.reconstruction:
            args.reconstruction.append(int(args.n_freq))
    
    freq_plot.set(
        {
            "render": args.render,
            "engine": args.engine,
            "dtw": args.dtw,
            "recon": args.reconstruction,
            "psd": args.psd,
            "transform": args.transformation,
            "name": args.plot_name
        }
    )
    freq_plot.plot()
