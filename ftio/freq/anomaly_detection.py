"""
------------------------------
Outlier detection methods
------------------------------
"""
# DB-scan
from __future__ import annotations
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from kneed import KneeLocator
from rich.panel import Panel
import matplotlib.pyplot as plt
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from sklearn.inspection import DecisionBoundaryDisplay
# Isolation forest
from sklearn.ensemble import IsolationForest
# Lof
from sklearn.neighbors import LocalOutlierFactor
# find_peaks
from scipy.signal import find_peaks
# all
import numpy as np
from ftio.freq.freq_plot_core import plot_both_spectrums
from ftio.freq.helper import format_plot



def outlier_detection(amp:np.ndarray, freq_arr:np.ndarray, args) -> tuple[list[float], np.ndarray, Panel]:
    """Find the outliers in the samples

    Args:
        A (list[float]): Amplitudes array
        freq_arr (list[float]): frequency array
        args (object, optional): arguments containgin: outlier detection method (Z-Score, DB-Scan). 
        Defaults to 'Z-score'.

    Returns:
        dominant_index (list[float]): indecies of dominant frequencies
        conf (list[float]): confidence in the predictions
        Panel: text to display using rich
    """
    methode = args.outlier
    text = ""    
    if methode.lower() in ["z-score", "zscore"]:
        dominant_index, conf, text = z_score(amp, freq_arr, args)
        title = "Z-score"
    elif methode.lower() in ["dbscan", "db-scan"]:
        dominant_index, conf, text = db_scan(amp, freq_arr, args)
        title = "DB-Scan"
    elif methode.lower() in ["isolation_forest", "forest"]:
        dominant_index, conf, text = isolation_forest(amp, freq_arr, args)
        title = "Isolation Forest"
    elif methode.lower() in ["local outlier factor", "lof"]:
        dominant_index, conf, text = lof(amp, freq_arr, args)
        title = "Local Outlier Factor"
    elif methode.lower() in ["find peaks", "peaks", "peak"]:
        dominant_index, conf, text = peaks(amp, freq_arr, args)
        title = "Find Peaks"
    else:
        dominant_index, conf = [],np.array([])
        raise NotImplementedError("Unsupported method selected")
    # sort dominant index according to confidence
    # if len(dominant_index) > 1:
    #     print(f"conf: {conf} and dominant_index {dominant_index}")
    #     tmp = conf[dominant_index]
    #     dominant_index = np.array(dominant_index)
    #     dominant_index = list(dominant_index[np.argsort(tmp)])
    text = Panel.fit(text[:-1], style="white", border_style='green', title=title, title_align='left')

    return dominant_index, conf, text


# ?#################################
# ? Z-score
# ?#################################
def z_score(
    amp: np.ndarray, freq_arr: np.ndarray, args
) -> tuple[list[float], np.ndarray, str]:
    """calculates the outliers using zscore

    Args:
        amp (np.ndarray): amplitude or psd
        freq_arr (np.ndarray): freuqencies
        args (argsparse): arguments

    Returns:
        tuple[list[float], np.ndarray, str]: [dominant freuqency/ies, confidence, text]
    """
    text = "[green]Spectrum[/]: Amplitude spectrum\n"
    if args.psd:
        amp = amp*amp/len(amp)
        text = "[green]Spectrum[/]: Power spectrum\n"

    indecies = np.arange(1, int(len(amp) / 2) + 1)
    amp_tmp = np.array(2 * amp[indecies])
    # norm the data
    amp_tmp = amp_tmp/ amp_tmp.sum()
    
    tol = args.tol
    dominant_index = []
    mean = np.mean(amp_tmp)
    std = np.std(amp_tmp)
    z_k = abs(amp_tmp - mean) / std
    conf = np.zeros(len(z_k))
    # find outliers
    index = np.where((z_k/np.max(z_k) > tol) & (z_k > 3))
    text += f"[green]mean[/]: {mean/np.sum(amp_tmp):.3e}\n[green]std[/]: {std:.3e}\n"
    text += f"Frequencies with Z-score > 3 -> [green]{len(z_k[z_k>3])}[/] candidates\n"
    text += f"         + Z > Z_max*{tol*100}% > 3 -> [green]{len(index[0])}[/] candidates\n"
    # text += f"         + Z > Z_max*{tol*100}% > 3 -> [green]{len(z_k[(z_k>np.max(z_k)*tol) & (z_k>3)])}[/] candidates\n"
    index, removed_index, msg = remove_harmonics(freq_arr, indecies[index[0]])
    text+= msg
    
    if len(index) == 0:
        text += "[red]No dominant frequency -> Signal might be not perodic[/]\n"
    else:
        removed_index = [i-1 for i in removed_index] #tmp starts at 1
        # conf[index] = (z_k[index]/max_z  + z_k[index]/np.sum(z_k[index]) + 1/np.sum(z_k > 3))/3
        # calculate the confidence:
        # 1) check z_k/max_zk > tol
        tmp = z_k/np.max(z_k) > tol
        tmp[removed_index] = False
        conf[tmp] += z_k[tmp]/np.sum(z_k[tmp])
        
        # 2) check z_k > 0
        tmp = z_k > 3
        tmp[removed_index] = False
        conf[tmp] += z_k[tmp]/np.sum(z_k[tmp])
        conf = conf/2
        conf = np.array(conf)
        

        # get dominant index
        dominant_index, msg = dominant(index, freq_arr, conf)
        text+= msg
        
    if "plotly" in args.engine:
        i = np.repeat(1, len(indecies))
        if len(dominant_index) != 0:
            i[np.array(dominant_index) - 1] = -1
        plot_outliers(args,freq_arr, amp, indecies, conf, i)

    return dominant_index, conf, text


# ?#################################
# ? DB-Scan
# ?#################################
def db_scan(
    amp: np.ndarray, freq_arr: np.ndarray, args
) -> tuple[list[float], np.ndarray, str]:
    """calculates the outliers using dbscan

    Args:
        amp (np.ndarray): amplitude or psd
        freq_arr (np.ndarray): freuqencies
        args (argsparse): arguments

    Returns:
        tuple[list[float], np.ndarray, str]: [dominant freuqency/ies, confidence]
    """
    text = "[green]Spectrum[/]: Amplitude spectrum\n" 
    if args.psd:
        amp = amp*amp/len(amp)
        text = "[green]Spectrum[/]: Power spectrum\n"
        
    indecies = np.arange(1, int(len(amp) / 2) + 1)
    amp_tmp = np.array(2 * amp[indecies])
    freq_arr_tmp = np.array(freq_arr[indecies])
    min_pts = 2

    # norm the data
    # d = np.vstack((freq_arr_tmp / freq_arr_tmp.max(), amp_tmp / amp_tmp.max())).T
    #! norm over sum for amplitude with power spectrum 
    d = np.vstack((freq_arr_tmp / freq_arr_tmp.max(), amp_tmp / amp_tmp.sum())).T

    eps_mode = "range"
    if eps_mode == "avr":
        text += "Calculating eps using average\n"
        try:
            eps = np.sqrt(pow(d[:, 1].mean(), 2) + pow(d[1, 0] - d[0, 0], 2))
        except ValueError:
            eps = 0.1
        conf = d[:, 1] / d[:, 1].max()
    elif eps_mode == "median":
        text += "Calculating eps using median\n"
        eps = np.sqrt(pow(np.median(d[:, 1]), 2) + pow(d[1, 0] - d[0, 0], 2))
        conf = d[:, 1] / d[:, 1].max()
    elif eps_mode == "range":
        text += "Calculating eps using range\n"
        eps = np.sqrt(
            pow((d[:, 1].max() - d[:, 1].min())*(1-args.tol), 2) + pow(d[1, 0] - d[0, 0], 2)
        )
        conf = d[:, 1] / d[:, 1].max()
    else:  # find distance using knee mehtod
        text += "Calculating eps using knee method\n"
        observation = int(len(amp) / 5)
        nbrs = NearestNeighbors(n_neighbors=observation).fit(d)
        # Find the k-neighbors of a point
        neigh_dist, _ = nbrs.kneighbors(d)
        # sort the neighbor distances (lengths to points) in ascending order
        sort_neigh_dist = np.sort(neigh_dist, axis=0)
        k_dist = sort_neigh_dist[:, observation - 1]  # sort_neigh_dist[:, 4]
        # plt.plot(k_dist)
        # plt.ylabel("k-NN distance")
        # plt.xlabel("Sorted observations (%ith NN)"%observation)
        # plt.show()
        kneedle = KneeLocator(
            x=range(1, len(neigh_dist) + 1),
            y=k_dist,
            S=1.0,
            curve="concave",
            direction="increasing",
            online=True,
        )
        eps = kneedle.knee_y
        conf = k_dist

    text += f"eps = [green]{eps:.4f}[/]    Minpoints = [green]{min_pts}[/]\n"
    model = DBSCAN(eps=eps, min_samples=min_pts)
    model.fit(d)
    dominant_index = model.labels_

    m_label = max(model.labels_)
    try:
        color = [
            px.colors.qualitative.Plotly[x]
            if (x >= 0)
            else px.colors.qualitative.Plotly[m_label + 1]
            for x in model.labels_
        ]
    except IndexError:
        if m_label > 10:
            color = [
                "blue" if (x >= 0) else "red"
                for x in model.labels_
            ]
        else:
            color = [
                px.colors.qualitative.Plotly[x] if (x >= 0) else "aliceblue"
                for x in model.labels_
            ]

    if "plotly" in args.engine:
        plot_dbscan(args, freq_arr, amp, indecies, conf, dominant_index, eps, color, d)

    clean_index, _, msg = remove_harmonics(freq_arr, indecies[dominant_index == -1])
    dominant_index,text_d = dominant(clean_index, freq_arr, conf)
    
    return dominant_index, conf,  text+msg+text_d


# ?#################################
# ? Isolation Forest
# ?#################################
def isolation_forest(
    amp: np.ndarray, freq_arr: np.ndarray, args
) -> tuple[list[float], np.ndarray, str]:
    """calculates the outliers using isolation forest

    Args:
        amp (np.ndarray): amplitude or psd
        freq_arr (np.ndarray): freuqencies
        args (argsparse): arguments

    Returns:
        tuple[list[float], np.ndarray, str]: [dominant freuqency/ies, confidence]
    """
    text = "[green]Spectrum[/]: Amplitude spectrum\n" 
    if args.psd:
        amp = amp*amp/len(amp)
        text = "[green]Spectrum[/]: Power spectrum\n"

    indecies = np.arange(1, int(len(amp) / 2) + 1)
    amp_tmp = np.array(2 * amp[indecies])
    freq_arr_tmp = np.array(freq_arr[indecies])
    # norm the data
    # d = np.vstack((freq_arr_tmp / freq_arr_tmp.max(), amp_tmp / amp_tmp.max())).T
    #! norm over sum for amplitude with power spectrum 
    d = np.vstack((freq_arr_tmp / freq_arr_tmp.max(), amp_tmp / amp_tmp.sum())).T

    model = IsolationForest(contamination=0.001, warm_start=True)
    # model = IsolationForest(contamination=float(0.001),warm_start=True, n_estimators=2)
    # model = IsolationForest(warm_start=True)
    model.fit(d)
    conf = model.decision_function(d)
    dominant_index = model.predict(d)

    if "plotly" in args.engine:
        plot_outliers(args, freq_arr, amp, indecies, conf, dominant_index, d)
        plot_decision_boundaries(model,d, conf)

    clean_index, _, msg = remove_harmonics(freq_arr, indecies[dominant_index == -1])
    dominant_index,text_d = dominant(clean_index, freq_arr, conf)
    
    return dominant_index, abs(conf), text+msg+text_d


# ?#################################
# ? Odin
# ?#################################
def lof(amp: np.ndarray, freq_arr: np.ndarray, args) -> tuple[list[float], np.ndarray, str]:
    """calculates the outliers using isolation lof

    Args:
        amp (np.ndarray): amplitude or psd
        freq_arr (np.ndarray): freuqencies
        args (argsparse): arguments

    Returns:
        tuple[list[float], np.ndarray, str]: [dominant freuqency/ies, confidence]
    """
    text = "[green]Spectrum[/]: Amplitude spectrum\n" 
    if args.psd:
        amp = amp*amp/len(amp)
        text = "[green]Spectrum[/]: Power spectrum\n"

    indecies = np.arange(1, int(len(amp) / 2) + 1)
    amp_tmp = np.array(2 * amp[indecies])
    freq_arr_tmp = np.array(freq_arr[indecies])

    # norm the data
    # d = np.vstack((freq_arr_tmp / freq_arr_tmp.max(), amp_tmp / amp_tmp.max())).T
    #! norm over sum for amplitude with power spectrum 
    d = np.vstack((freq_arr_tmp / freq_arr_tmp.max(), amp_tmp / amp_tmp.sum())).T

    model = LocalOutlierFactor(contamination=0.001, novelty=True)
    model.fit(d)
    conf = model.decision_function(d)
    dominant_index = model.predict(d)

    # plot
    if "plotly" in args.engine:
        plot_outliers(args, freq_arr, amp, indecies, conf, dominant_index, d)

    clean_index, _, msg = remove_harmonics(freq_arr, indecies[dominant_index == -1])
    dominant_index,text_d = dominant(clean_index, freq_arr, conf)
    
    return dominant_index, abs(conf), text+msg+text_d


# ?#################################
# ? find_peaks
# ?#################################
def peaks(amp: np.ndarray, freq_arr: np.ndarray, args) -> tuple[list[float], np.ndarray, str]:
    """calculates the outliers using isolation lof

    Args:
        amp (np.ndarray): amplitude or psd
        freq_arr (np.ndarray): freuqencies
        args (argsparse): arguments

    Returns:
        tuple[list[float], np.ndarray, str]: [dominant freuqency/ies, confidence]
    """
    text = "[green]Spectrum[/]: Amplitude spectrum\n" 
    if args.psd:
        amp = amp*amp/len(amp)
        text = "[green]Spectrum[/]: Power spectrum\n"

    indecies = np.arange(1, int(len(amp) / 2) + 1)
    amp_tmp = np.array(2 * amp[indecies])
    freq_arr_tmp = np.array(freq_arr[indecies])
    
    # norm the data
    # d = np.vstack((freq_arr_tmp / freq_arr_tmp.max(), amp_tmp / amp_tmp.max())).T
    #! norm over sum for amplitude with power spectrum 
    d = np.vstack((freq_arr_tmp / freq_arr_tmp.max(), amp_tmp / amp_tmp.sum())).T

    limit = 1.2*np.mean(d[:,1])
    found_peaks, _ = find_peaks(d[:,1], height= limit if limit > 0.2 else 0.2)
    conf = np.zeros(len(d[:,1]))
    conf[found_peaks] = 1
    dominant_index = np.zeros(len(d[:,1]))
    dominant_index[found_peaks] = -1

    # plot
    if "plotly" in args.engine:
        plot_outliers(args, freq_arr, amp, indecies, conf, dominant_index, d)

    clean_index, _, msg = remove_harmonics(freq_arr, indecies[dominant_index == -1])
    dominant_index,text_d = dominant(clean_index, freq_arr, conf)
    
    return dominant_index, abs(conf), text+msg+text_d


def dominant(
    dominant_index: np.ndarray, freq_arr: np.ndarray, conf: np.ndarray
) -> tuple[list[float],str]:
    """_summary_

    Args:
        dominant_index (array): found indecies of dominant frequencies
        freq_arr (array): array of frequencies
        conf (float): value between -1 (strong outlier) and 1 (no outlier)

    Returns:
        dominant_index: set to 0 if more than three were found. Also remove harmonics
        text: text information
    """
    text = ""
    out = []
    if len(dominant_index) > 0:
        for i in dominant_index:
            if any(freq_arr[i] % freq_arr[out] < 0.00001):
                text += f"[yellow]Ignoring harmonic at: {freq_arr[i]:.3e} Hz (T = {1/freq_arr[i] if freq_arr[i] > 0 else 0:.3f} s, k = {i}) -> confidence: {abs(conf[i-1])*100:.3f}%[/]\n"
            else:
                text += f"Dominant frequency at: [green] {freq_arr[i]:.3e} Hz (T = {1/freq_arr[i] if freq_arr[i] > 0 else 0:.3f} s, k = {i}) -> confidence: {abs(conf[i-1])*100:.3f}%[/]\n"
                out.append(i)
            if len(out) > 2:
                text = "[red]Too many dominant frequencies -> Signal might be not perodic[/]\n"
                out = []
                break
    else: 
        text = "[red]No dominant frequencies found -> Signal might be not perodic[/]\n"
    
    return out, text


def remove_harmonics(freq_arr,index_list) -> tuple[np.ndarray, list, str]:
    """Removes harmonics

    Args:
        freq_arr (_type_): frequency array
        index_list (_type_): list of indecies starting at 1

    Returns:
        np.ndarray: indecies without harmonics
        list: removed harmonics
        str: text to print
    """
    seen = []
    removed = []
    msg = ""
    flag = True
    for ind in index_list:
        if seen:
            flag = True
            for value in seen:
                if freq_arr[ind] % freq_arr[value] < 0.00001 and ind != value:
                    msg += (
                        f"[yellow]Ignoring harmonic at: {freq_arr[ind]:.3e} Hz "
                        f"(T = {1/freq_arr[ind] if freq_arr[ind] > 0 else 0:.3f} s, k = {ind})[/]\n"
                        )
                    removed.append(ind)
                    flag = False
                    break
            if flag and ind not in seen:
                seen.append(ind)
        else:
            seen.append(ind)
    return np.array(seen), removed, msg




# ?#################################
# ? Plot outliers
# ?#################################
def plot_outliers(
    args,
    freq_arr: np.ndarray,
    amp: np.ndarray,
    indecies: np.ndarray,
    conf: np.ndarray,
    dominant_index: np.ndarray,
    d: np.ndarray = np.array([])
) -> None:
    """Plots outliers

    Args:
        freq_arr (np.ndarray): _description_
        amp (np.ndarray): aplitude or power 
        indecies (np.ndarray): _description_
        conf (np.ndarray): _description_
        dominant_index (np.ndarray): _description_
        d (np.ndarray, optional): _description_. Defaults to np.array([]).
    """
    name = "Amplitude"
    if args.psd:
        name = "Power"

    if d.size == 0 and len(freq_arr) != 0:
        d = np.vstack(
            (
                freq_arr[indecies] / freq_arr[indecies].max(),
                amp[indecies] / amp[indecies].sum(),
            )
        ).T
    elif len(freq_arr) == 0:
        return
    else:
        pass

    names = [(f"cluster {i}") if (i >= 0) else "outliers" for i in dominant_index]
    fig_main = make_subplots(
        rows=4,
        cols=2,
        specs=[
            [{}, {}],
            [{"colspan": 2}, None],
            [{"colspan": 2}, None],
            [{"colspan": 2}, None]
            ],
            horizontal_spacing = 0.2
    )
    # f1 = make_subplots(rows=2, cols=1)
    fig_0 = px.scatter(
        d, x=0, y=1, color=names, labels={"0": "Frequency (Hz)", "1": name}
    )
    for trace in list(fig_0.select_traces()):
        fig_main.append_trace(trace, row=2, col=1)

    fig_main.update_traces(
        hovertemplate="<b>freq: %{x:.4f}    Hz<br>" + "Amplitude: %{y:.2f}<br>"
    )
    fig_main.add_trace(
        go.Scatter(
            x=d[:, 0],
            y=d[:, 1],
            mode="markers",
            marker=dict(color=conf),
            text=conf,
            hovertemplate="<b>Noremed values<br><br>Freq: %{x:.4f}  <br>"
            + "Amplitude: %{y:.2f}<br>"
            + "conf: %{text:.2f}",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    fig_main.add_trace(
        go.Scatter(
            x=freq_arr[indecies],
            y=2*amp[indecies],
            mode="markers",
            marker=dict(color=dominant_index),
            text=dominant_index,
            hovertemplate="<b>Freq: %{x:.4f}    Hz<br>"
            + "Amplitude: %{y:.2f}<br>"
            + "cluster: %{text:.2f}",
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    counter = 2
    figs,names = plot_both_spectrums(args,freq_arr, amp, full = False)
    for trace in list(figs.select_traces()):
        counter += 1
        trace.update(marker={'coloraxis': f'coloraxis{counter}'})
        fig_main.append_trace(trace, row=counter, col=1)
    fig_main.update_layout(
    coloraxis3={
        "colorbar": {
            "x": 1,
            "len": .2,
            "y": 0.36,
        },
        "colorscale": ["rgb(0,50,150)", "rgb(150,50,150)", "rgb(255,50,0)"] #'Bluered'
    },
    coloraxis4={
        "colorbar": {
            "x": 1,
            "len": .2,
            "y": .09,
        },
        "colorscale": ["rgb(0,50,150)", "rgb(150,50,150)", "rgb(255,50,0)"] #'Bluered'
    }
    )
    
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=1, range=[-.01,1.01])
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=2, row=1)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=2, range=[-.01,1.01])
    fig_main.update_yaxes(title_text=f"Normed {name}", col=1, row=1)
    fig_main.update_yaxes(title_text=f"{name}", col=2, row=1)
    fig_main.update_yaxes(title_text=f"Normed {name}", col=1, row=2)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=4)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=3)
    fig_main.update_yaxes(title_text=names[0], col=1, row=3)
    fig_main.update_yaxes(title_text=names[1], col=1, row=4)
    fig_main.update_layout(
        width=1300, 
        height=1700, 
        font={"family": "Courier New, monospace", "size": 24, "color": "black"},
        template="plotly",
        )
    format_plot(fig_main)
    fig_main.show()


def plot_dbscan(
    args,
    freq_arr: np.ndarray,
    amp: np.ndarray,
    indecies: np.ndarray,
    conf: np.ndarray,
    dominant_index: np.ndarray,
    eps,
    color,
    d: np.ndarray = np.array([]),
    ) -> None:
    """Plots outliers for DB scan

    Args:
        freq_arr (np.ndarray): _description_
        amp (np.ndarray): aplitude or power 
        indecies (np.ndarray): _description_
        conf (np.ndarray): _description_
        dominant_index (np.ndarray): _description_
        d (np.ndarray, optional): _description_. Defaults to np.array([]).
    """
    mode = "Amplitude"
    if args.psd:
        mode = "Power"
    names = [(f"cluster {i}") if (i >= 0) else "outliers" for i in dominant_index]
    fig_main = make_subplots(
        rows=4,
        cols=2,
        specs=[
            [{}, {}],
            [{"colspan": 2}, None],
            [{"colspan": 2}, None],
            [{"colspan": 2}, None]
            ]
    )

    fig_main.add_trace(
        go.Scatter(
            x=d[:, 0],
            y=d[:, 1],
            mode="markers",
            marker=dict(color=color),
            text=names,
            hovertemplate="<b>Noremed values<br><br>Freq: %{x:.4f}  <br>"
            + "Amplitude: %{y:.2f}<br>"
            + "cluster: %{text}",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig_main.update_traces(
        hovertemplate="<b>freq: %{x:.4f}    Hz<br>" + "Amplitude: %{y:.2f}<br>"
    )
    fig_main.add_trace(
        go.Scatter(
            x=d[:, 0],
            y=d[:, 1],
            mode="markers",
            marker=dict(color=color),
            text=names,
            hovertemplate="<b>Noremed values<br><br>Freq: %{x:.4f}  <br>"
            + "Amplitude: %{y:.2f}<br>"
            + "cluster: %{text}",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    fig_main.add_trace(
        go.Scatter(
            x=freq_arr[indecies],
            y=2*amp[indecies],
            mode="markers",
            marker=dict(color=conf),
            text=names,
            hovertemplate="<b>Freq: %{x:.4f}    Hz<br>"
            + "Amplitude: %{y:.2f}<br>"
            + "cluster: %{text}",
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    for i in range(0, len(d)):
        fig_main.add_shape(
            dict(
                type="circle",
                x0=d[i, 0] - eps,
                y0=d[i, 1] - eps,
                x1=d[i, 0] + eps,
                y1=d[i, 1] + eps,
                opacity=0.3,
            ),
            row=1,
            col=1,
            name=names[i],
            line_color=color[i],
        )

    counter = 2
    figs = plot_both_spectrums(args,freq_arr, amp, full = False)
    for trace in list(figs.select_traces()):
        counter += 1
        trace.update(marker={'coloraxis': f'coloraxis{counter}'})
        fig_main.append_trace(trace, row=counter, col=1)
    fig_main.update_layout(
    coloraxis3={
        "colorbar": {
            "x": 1,
            "len": .2,
            "y": 0.36,
        },
        "colorscale": ["rgb(0,50,150)", "rgb(150,50,150)", "rgb(255,50,0)"] #'Bluered'
    },
    coloraxis4={
        "colorbar": {
            "x": 1,
            "len": .2,
            "y": .09,
        },
        "colorscale": ["rgb(0,50,150)", "rgb(150,50,150)", "rgb(255,50,0)"] #'Bluered'
    })

    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=1)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=2, row=1)
    fig_main.update_xaxes(title_text="Frequency (Hz)", col=1, row=2)
    fig_main.update_yaxes(title_text=f"Normed {mode}", col=1, row=1)
    fig_main.update_yaxes(title_text=f"Normed {mode}", col=2, row=1)
    fig_main.update_yaxes(title_text=f"Normed {mode}", col=1, row=2)
    # fig_1.update_xaxes(title_text="Frequency (Hz)", col=1, row=4)
    # fig_1.update_xaxes(title_text="Frequency (Hz)", col=1, row=3)
    # fig_1.update_yaxes(title_text="Amplitude", col=1, row=3)
    # fig_1.update_yaxes(title_text="Normed Power (%)", col=1, row=4)
    format_plot(fig_main)
    fig_main.update_layout(width=1200, height=1400, font=dict(family="Courier New, monospace"), size=13)
    fig_main.show()


def plot_decision_boundaries(model, d, conf):
    disp = DecisionBoundaryDisplay.from_estimator(
        model,
        d,
        response_method="decision_function",
        alpha=0.5,
    )
    disp.ax_.scatter(d[:, 0], d[:, 1], c=conf, s=20, edgecolor="k")
    disp.ax_.set_title("Binary decision boundary \nof IsolationForest")
    plt.axis("square")
    plt.legend(labels=["outliers", "inliers"], title="true class")
    plt.show()