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

CONSOLE = MyConsole()



def display_prediction(
    argv: str | Namespace = "ftio", prediction: dict | list[dict] = {}
) -> None:
    """
    Displays the result of the prediction from ftio.

    Args:
        argv (str | Namespace): Command-line arguments or parsed arguments.
        prediction (dict | list[dict]): The result from ftio.
    """

    # Handle multiple predictions
    if isinstance(prediction, list):
        for pred in prediction:
            display_prediction(argv, pred)
        return

    # Display results if prediction is available
    if prediction:
        freq, conf = get_dominant_and_conf(prediction)
        if not np.isnan(freq):
            CONSOLE.info(
                f"[cyan underline]Prediction results:[/]\n[cyan]Frequency:[/] {freq:.3e} Hz"
                f"[cyan] ->[/] {np.round(1/freq, 4)} s\n"
                f"[cyan]Confidence:[/] {color_pred(conf)}"
                f"{np.round(conf * 100, 2)}[/] %\n"
            )
        else:
            CONSOLE.info(
                "[cyan underline]Prediction results:[/]\n"
                "[red]No dominant frequency found[/]\n"
            )
    # If -n is provided, print the top frequencies with their confidence and amplitude in a table
    if isinstance(argv, Namespace) and argv.n_freq > 0:
        CONSOLE.info(f"[cyan underline]Top {int(argv.n_freq)} Frequencies:[/]")
        if "top_freq" in prediction:
            freq_array = prediction["top_freq"]["freq"]
            conf_array = np.round(np.where(np.isinf(prediction["top_freq"]["conf"]), 1, prediction["top_freq"]["conf"]) * 100, 2)
            amp_array = prediction["top_freq"]["amp"]

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Freq (Hz)", justify="right", style="white", no_wrap=True)
            table.add_column("Conf. (%)", justify="right", style="white", no_wrap=True)
            table.add_column("Amplitude", justify="right", style="white", no_wrap=True)

            # Add frequency data
            for i, freq in enumerate(freq_array):
                table.add_row(f"{freq:.3e}", f"{conf_array[i]:.2f}", f"{amp_array[i]:.3e}")

            CONSOLE.info(table)
        else:
            CONSOLE.info("[red]No top frequency data found[/]")

    # # If -n is provided, print the top frequencies with their confidence and amplitude in a table-like format
    # if isinstance(argv, Namespace) and argv.n_freq > 0:

    #     if "top_freq" in prediction:
    #         freq_array = prediction["top_freq"]["freq"]
    #         conf_array = prediction["top_freq"]["conf"]
    #         conf_array = np.round(np.where(np.isinf(conf_array), 1, conf_array) * 100, 2)
    #         amp_array = prediction["top_freq"]["amp"]

    #         # Print the table header
    #         text += f"{'Freq (Hz)':<12}{'Conf. (%)':12}{'Amplitude':<10}\n"
    #         text += "-" * 33 + "\n"

    #         # Print the top frequencies in a table-like format
    #         for i,freq in enumerate(freq_array):
    #             text += f"{freq:<12.3e}{conf_array[i]:<12}{amp_array[i]:<10.3e}\n"
    #     else:
    #         text += "[red]No top frequency data found[/]\n"

    #     CONSOLE.info(Panel(text, title="[bold cyan]Prediction Results[/]", border_style="cyan"))


