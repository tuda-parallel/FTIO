"""
Module for displaying prediction results from the ftio package.

This module provides functionality to process and display prediction results on the console.
"""

from argparse import Namespace
import numpy as np
from rich.table import Table
from ftio.prediction.unify_predictions import color_pred
from ftio.prediction.helper import get_dominant_and_conf
from ftio.freq.helper import MyConsole
from ftio.freq.prediction import Prediction


def display_prediction(
    argv: str | Namespace = "ftio",
    prediction: Prediction | list[Prediction] = Prediction(),
) -> None:
    """
    Displays the result of the prediction from ftio.

    Args:
        argv (str | Namespace): Command-line arguments or parsed arguments.
        prediction (Prediction | list[Prediction]): The result from ftio.
    """

    # Handle multiple predictions
    if isinstance(prediction, list):
        for pred in prediction:
            display_prediction(argv, pred)
        return

    console = MyConsole()
    # Display results if prediction is available
    if prediction:
        freq, conf = prediction.get_dominant_freq_and_conf()
        if not np.isnan(freq):
            console.info(
                f"[cyan underline]Prediction results:[/]\n[cyan]Frequency:[/] {freq:.3e} Hz"
                f"[cyan] ->[/] {np.round(1/freq, 4)} s\n"
                f"[cyan]Confidence:[/] {color_pred(conf)}"
                f"{np.round(conf * 100, 2)}[/] %\n"
            )
        else:
            console.info(
                "[cyan underline]Prediction results:[/]\n" "[red]No dominant frequency found[/]\n"
            )
    # If -n is provided, print the top frequencies with their confidence and amplitude in a table
    if isinstance(argv, Namespace) and argv.n_freq > 0:
        console.info(f"[cyan underline]Top {int(argv.n_freq)} Frequencies:[/]")
        if prediction.top_freqs:
            freq_array = prediction.top_freqs["freq"]
            conf_array = np.round(
                np.where(np.isinf(prediction.top_freqs["conf"]), 1, prediction.top_freqs["conf"])
                * 100,
                2,
            )
            amp_array = prediction.top_freqs["amp"]
            phi_array = prediction.top_freqs["phi"]

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Freq (Hz)", justify="right", style="white", no_wrap=True)
            table.add_column("Conf. (%)", justify="right", style="white", no_wrap=True)
            table.add_column("Amplitude", justify="right", style="white", no_wrap=True)
            table.add_column("Phi", justify="right", style="white", no_wrap=True)
            table.add_column("Cosine Wave", justify="right", style="white", no_wrap=True)

            description = ""
            # Add frequency data
            for i, freq in enumerate(freq_array):
                if freq == 0 or freq == prediction.freq / 2:
                    cosine_wave = f"{1 / prediction.n_samples * amp_array[i]:.3e}*cos(2\u03c0*{freq:.3e}*t{' +' if phi_array[i] >= 0 else ' -'}{abs(phi_array[i]):.3e})"
                else:
                    cosine_wave = f"{2 / prediction.n_samples * amp_array[i]:.3e}*cos(2\u03c0*{freq:.3e}*t{' +' if phi_array[i] >= 0 else ' -'}{abs(phi_array[i]):.3e})"
                table.add_row(
                    f"{freq:.3e}",
                    f"{conf_array[i]:.2f}",
                    f"{amp_array[i]:.3e}",
                    f"{phi_array[i]:.3e}",
                    cosine_wave,
                )
                if i == 0:
                    description = cosine_wave
                else:
                    description += " + " + cosine_wave

            console.info(table)
            console.info(f"Carterization up to {argv.n_freq} frequencies: \n{description}\n")
        else:
            console.info("[red]No top frequency data found[/]")
