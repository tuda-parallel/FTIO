"""
This module contains operations for processing and plotting data using ftio.
"""

from rich.console import Console
from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args
from ftio.freq._dft import display_prediction
from ftio.plot.freq_plot import convert_and_plot

console = Console()


def quick_ftio(
    argv: list,
    b: list,
    t: list,
    total_bytes: int,
    ranks: int,
    msg: str = "",
    verbose: bool = True,
) -> dict:
    """Quickly process and plot data using ftio.

    Args:
        argv (list): Command line arguments.
        b (list): Bandwidth data.
        t (list): Time data.
        total_bytes (int): Total bytes data.
        ranks (int): MPI Ranks.
        msg (str): Message to display.
        verbose (bool, optional): Whether to display verbose output. Defaults to True.

    Returns:
        dict: Prediction results.
    """
    # set up data
    data = {"time": t, "bandwidth": b, "total_bytes": total_bytes, "ranks": ranks}

    # parse args
    args = parse_args(argv, "ftio")

    # perform prediction
    prediction, dfs = core(data, args)

    # plot and print info
    convert_and_plot(args, dfs, len(data))

    if verbose and len(msg) > 0:
        console.print(f"[green]>> Prediction for {msg}[/]")
        display_prediction("ftio", prediction)

    return prediction
