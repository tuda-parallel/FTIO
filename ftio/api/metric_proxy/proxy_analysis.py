import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ftio.freq.helper import MyConsole
from ftio.plot.print_html import PrintHtml
from ftio.plot.helper import format_plot

CONSOLE = MyConsole()
CONSOLE.set(True)


def phases_and_timeseries(metrics, data, argv=[]):
    phasemode_list, t = classify_waves(data, True)

    if argv and '-n' in argv:
        n = argv[argv.index('-n') + 1]
        plot_waves_and_timeseries(metrics, phasemode_list, t, n)
    else:
        plot_waves_and_timeseries(metrics, phasemode_list, t)


def phases(data, argv=[]):
    phasemode_list, t = classify_waves(data)

    if argv and '-n' in argv:
        n = argv[argv.index('-n') + 1]
        plot_waves(phasemode_list, t, n)
    else:
        plot_waves(phasemode_list, t)


def classify_waves(data, normed=True):
    phasemode_list = []
    phasemode_list.append(
        PhaseMode(
            'Network',
            [
                'network',
                'mpi_bcast',
                'sock',
                'send',
                'listen',
                'recieve',
                'gather',
                'reduce',
                'cast',
            ],
        )
    )
    phasemode_list.append(PhaseMode('write', ['write']))
    phasemode_list.append(PhaseMode('read', ['read']))
    phasemode_list.append(
        PhaseMode(
            'I/O',
            [
                'io',
                'disk',
                'stat',
                'cntl',
                'read',
                'write',
                'openat',
                'mmap',
                'seek',
                'close',
            ],
        )
    )
    phasemode_list.append(PhaseMode('Temperature', ['temp']))
    phasemode_list.append(PhaseMode('CPU', ['cpu']))
    phasemode_list.append(PhaseMode('Wait', ['poll', 'barrier']))
    seen = []
    for mode in phasemode_list:
        seen.extend(mode.matches)
    other = [x['metric'] for x in data if all(y not in x['metric'] for y in seen)] 
    phasemode_list.append(PhaseMode('Other', other))

    sampling_freq = np.NaN
    t_s = np.NaN
    t_e = np.NaN
    for d in data:
        if len(d['dominant_freq']) > 0 and len(d['conf']) > 0:
            if np.isnan(sampling_freq):
                sampling_freq = d['freq']
                t_s = d['t_start']
                t_e = d['t_end']

            add_metric(phasemode_list, d)

    t = np.arange(t_s, t_e, 1 / sampling_freq)
    text = print_len(phasemode_list, data)
    CONSOLE.print(f'[blue]{text}[/]')
    calculate_waves(phasemode_list, t, normed)

    return phasemode_list, t


class PhaseMode:
    def __init__(self, name: str, matches: list[str]) -> None:
        self.name = name
        self.matches = matches
        self.data = []
        self.wave = np.nan

    def match(self, d: dict):
        if any(n in d['metric'] for n in self.matches):
            return True
        else:
            return False

    def add(self, d: dict) -> None:
        self.data.append(d)

    def calculate_wave(self, t, normed=True):
        self.wave = np.zeros(len(t))
        for i in self.data:
            if 'top_freq' in i:
                for j in range(0, len(i['top_freq']['freq'])):
                    self.wave = self.wave + i['top_freq']['amp'][j] * np.cos(
                        2 * np.pi * i['top_freq']['freq'][j] * t
                        + i['top_freq']['phi'][j]
                    )
            else:
                max_conf_index = np.argmax(i['conf'])
                self.wave = self.wave + i['amp'][max_conf_index] * np.cos(
                    2 * np.pi * i['dominant_freq'][max_conf_index] * t
                    + i['phi'][max_conf_index]
                )
                # self.wave = self.wave +np.cos(2* np.pi*i['dominant_freq'][max_conf_index]*t +  i['phi'][max_conf_index])
        if normed:
            self.wave = norm(self.wave)


def plot_waves(arr: list[PhaseMode], t, n=None):
    fig = go.Figure()
    for mode in arr:
        fig.add_trace(
            go.Scatter(x=t, y=mode.wave, mode='lines+markers', name=mode.name)
        )

    fig.update_layout(
        xaxis_title='Time (s)',
        yaxis_title='Normed metrics',
    )
    if n:
        fig.update_layout(legend_title_text=f'{n} Frequencies')
    fig.show()
    # fig.write_image("waves.png")


def plot_waves_and_timeseries(metrics: dict, arr: list[PhaseMode], t, n=None):
    names = [] #get_names(arr)

    out = PrintHtml('./', names, outdir='phase_plots')
    out.generate_html_start()
    # t = []
    for mode in arr:
        f = plot_mode(mode,metrics,t,n,True)
        # for fig in f:
        #     fig.show
        out.generate_html_core(mode.name+'.html', f)

    out.generate_html_end()


def plot_mode(mode,metrics,t,n,subfig=False)-> list[go.Figure]:

    f = []
    spec=[{},{}]
    if subfig:
        f.append(make_subplots(rows=2,cols=1))
        spec=[{"row":1,"col":1},{"row":2,"col":1}]
    else:
        f.append(go.Figure())

    f[-1].add_trace(
        go.Scatter(x=t, y=mode.wave, mode='lines+markers', name=mode.name),**spec[0])

    if not subfig:
        f.append(go.Figure())

    for metric, arrays in metrics.items():
        if len(arrays[0]) > 1 and any(n in metric for n in mode.matches):
            f[-1].add_trace(
                go.Scatter(
                    x=arrays[1],
                    y=arrays[0],
                    mode='lines+markers',
                    name=metric,
                    hovertemplate='<i>Time </i>: %{x} s'
                    + '<br><b>Metric</b>: %{y}<br>',
                ),**spec[1]
            )

    for fig in f:
        fig = format_plot(fig, font=False)
        fig.update_layout(
            xaxis_title='Time (s)',
            yaxis_title=f'{mode.name.capitalize()} Metrics',
            width=1400,
            height=800,
            showlegend=True,
        ) 
    if subfig:
        fig.update_xaxes(title_text='Time (s)', **spec[1])
        fig.update_yaxes(title_text=f'{mode.name.capitalize()} Metrics',**spec[1])

        if f.index(fig) == 0:
            if n:
                fig.update_layout(title=f'{mode.name.capitalize()}: Using {n} Frequencies per metric')
            else:
                fig.update_layout(title=f'{mode.name.capitalize()}: Using Dominant Frequencies')
    return f

def norm(wave: np.ndarray) -> np.ndarray:
    max_value = np.max(np.abs(wave))
    normed_wave = wave / max_value if max_value > 0 else wave
    return normed_wave


def add_metric(arr: list[PhaseMode], d):
    for mode in arr:
        if mode.match(d):
            mode.add(d)
            break

def get_names(arr:list[PhaseMode])-> list[str]:
    names = []
    for mode in arr:
        names.append(mode.name)
    return names 


def calculate_waves(arr: list[PhaseMode], t, normed=True):
    for mode in arr:
        mode.calculate_wave(t, normed)


def print_len(arr: list[PhaseMode], data) -> str:
    text = '\n'
    total_metrics = 0
    for mode in arr:
        text += f'{len(mode.data):3} {mode.name} metrics\n'
        total_metrics += len(mode.data)

    text += f'---------------------\n{total_metrics:3}/{len(data):3} total metrics with dominant frequencies\n'

    return text
