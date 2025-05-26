from argparse import Namespace
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import plotly.graph_objs as go
from ftio.freq.helper import MyConsole
from ftio.freq.prediction import Prediction
from ftio.freq._analysis_figures import AnalysisFigures


def fourier_sum(t:np.ndarray, *params) -> np.ndarray:
    """
    Computes the sum of multiple cosine functions (Fourier components) with given amplitudes, frequencies, and phases.

    Args:
        t (np.ndarray): Input array representing time or the independent variable.
        *params : Variable length argument list. Each group of three values corresponds to the amplitude, frequency,
        and phase of a cosine component, in the order: [amp1, freq1, phi1, amp2, freq2, phi2, ...].

    Returns:
        out (np.ndarray) : ndarray
            Array of the same shape as `t`, containing the sum of the cosine components evaluated at each value of `t`.
    """
    out = np.zeros_like(t)
    n = len(params)//3
    for i in range(n):
        amp = params[3*i]
        freq = params[3*i+1]
        phi = params[3*i+2]
        out += amp * np.cos(2 * np.pi * freq * t + phi)
    return out


def fourier_fit(args:Namespace, prediction:Prediction, analysis_figures:AnalysisFigures, b_sampled:np.ndarray, t:np.ndarray, maxfev:int = 10000) -> None:
    """
    Fits a sum of Fourier components to sampled data using non-linear least squares.
    Parameters. Finds the best frequencies (and other params) by minimizing error, starting from initial guess
    (usually DFT peaks). It:
    - Finds frequencies off the DFT grid (non-integer multiples)
    - Refines amplitude and phase estimates
    - Handles noise better by fitting parameters globally
    - Uses initial guesses often derived from the DFT maxima

    The filed top_freq is changed in Prediction is overwritten by the new results

    Args:
        args : Namespace
            Arguments containing configuration, must include 'n_freq' (number of frequencies).
        prediction : Prediction
            Prediction class containing initial predictions for amplitudes ('amp'), frequencies ('freq'), and phases ('phi')
            under the field 'top_freq'.
        b_sampled : np.ndarray
            Sampled signal data to fit.
        t : np.ndarray
            Time points corresponding to the sampled data.
        maxfev : int, optional
            Maximum number of function evaluations for the optimizer (default is 10000).
    Returns:
        None
    """
    if args.reconstruction:
        if max(args.reconstruction) < args.n_freq:
            args.reconstruction.append(args.n_freq)
    p0 = []
    n = len(b_sampled)
    for i in range(args.n_freq):
        if prediction.top_freqs["freq"][i] == 0:
            scale = 1 / n
        else:
            scale = 2 / n

        p0 += [
            scale*prediction.top_freqs["amp"][i],
            prediction.top_freqs["freq"][i],
            prediction.top_freqs["phi"][i]
               ]

    # Fit Fourier sum model
    # params_opt, _ = curve_fit(fourier_sum, x, cA, p0=p0, maxfev=10000)
    params_opt, _ = curve_fit(fourier_sum, t, b_sampled, p0=p0,maxfev=maxfev)


    opt_mag  = params_opt[0::3] # Magnitude is 2*amp/n
    opt_amp = np.zeros_like(opt_mag)
    opt_freq = params_opt[1::3]
    opt_phi  =  params_opt[2::3]
    for i, freq in enumerate(opt_freq):
        if freq == 0:
            opt_amp[i] = n*opt_mag[i]
        else:
            opt_amp[i] = n*opt_mag[i]/2


    #  Adapt negative freq, as these require flipping phi:
    opt_phi  = np.where(opt_freq < 0, -opt_phi, opt_phi)
    opt_freq = np.abs(opt_freq)

    prediction.set("top_freqs",{
        "conf": np.repeat(1,args.n_freq),
        "amp":  opt_amp,
        "freq": opt_freq,
        "phi":  opt_phi,
    })

    if any(x in args.engine for x in ["mat", "plot"]):
        console = MyConsole()
        console.set(args.verbose)
        console.print(f"Generating Fourier Fit Plot\n")
        fig = plot_fourier_fit(args, t, b_sampled, prediction, fourier_sum(t, *params_opt))
        analysis_figures.add_figure_and_show([fig], "fourier_fit")
        console.print(f" --- Done --- \n")

def plot_fourier_fit(args: Namespace, t: np.ndarray, b_sampled: np.ndarray,prediction:Prediction, cA_fourier_fit, show_top=False):
    """
    Plot sampled signal and Fourier sum using either matplotlib or plotly
    depending on args.engine content.

    Args:
        args: Object with attribute 'engine' specifying plotting backend
        t (array-like): Time vector
        b_sampled (array-like): Sampled signal data
        prediction : Prediction from FTIO
        cA_fourier_fit (array-like): Fourier sum data
        show_top (bool, optional): If True, show the top frequencies

    Returns:
        matplotlib.figure.Figure or plotly.graph_objs.Figure:
            Figure object for further manipulation or display.
    """

    if "mat" in args.engine.lower():
        # Matplotlib plotting
        fig, ax = plt.subplots()
        ax.plot(t, b_sampled, linestyle='--', label='sampled signal')
        ax.plot(t, cA_fourier_fit, label='Fourier Sum')
        if show_top:
            N = len(prediction.top_freqs["freq"])
            for k in range(N):
                a = prediction.top_freqs["amp"][k] / N
                if k != 0 and not (N % 2 != 0 and k == N - 1):
                    a *= 2
                    ax.plot(
                        t,
                        a * np.cos(2 * np.pi * prediction.top_freqs["freq"][k] * t + prediction.top_freqs["phi"][k]),
                        label=f"{a:.1e}*cos(2\u03C0*{prediction.top_freqs['freq'][k]:.2e}*t+{prediction.top_freqs['phi'][k]:.2e})"
                    )
        ax.legend()
    else:
        # Plotly plotting
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=b_sampled, mode='lines', name='sampled signal', line=dict(dash='dash')))
        fig.add_trace(go.Scatter(x=t, y=cA_fourier_fit, mode='lines', name='Fourier Sum'))
        if show_top:
            N = len(prediction.top_freqs["freq"])
            for k in range(N):
                a = prediction.top_freqs["amp"][k] / N
                if k != 0 and not (N % 2 != 0 and k == N - 1):
                    a *= 2
                    fig.add_trace(go.Scatter(
                        x=t,
                        y=a * np.cos(2 * np.pi * prediction.top_freqs["freq"][k] * t + prediction.top_freqs["phi"][k]),
                        mode = 'lines',
                        name=f"{a:.1e}*cos(2\u03C0*{prediction.top_freqs["freq"][k]:.2e}*t+{prediction.top_freqs["phi"][k]:.2e})"
                    ))

    return fig
