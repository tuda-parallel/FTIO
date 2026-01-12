"""
# Time Window functions
This file contains function that allow modifying and setting the data according the the time window:
- data_in_time_window: cuts the data according the start and end time specified by the arguments.
"""

import numpy as np


def data_in_time_window(
    args,
    bandwidth: np.ndarray,
    time_b: np.ndarray,
    total_bytes: int,
    ranks: int = 0,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Cuts the data according the start and end time specified by the arguments.

    Args:
        args (_type_): argparse
        bandwidth (np.ndarray)
        time_b (np.ndarray)
        total_bytes (int)
        ranks (int, optional). Defaults to 0.

    Returns:
        tuple[np.ndarray,np.ndarray,str]: cut bandwidth and time + text
    """
    text = f"Ranks: [cyan]{ranks}[/]\n"
    ignored_bytes = total_bytes
    # shorten data according to start time
    if args.ts:
        indices = np.where(time_b >= args.ts)
        time_b = time_b[indices]
        bandwidth = bandwidth[indices]
        
        if len(time_b) > 0:
            total_bytes = int(
                np.sum(bandwidth * (np.concatenate([time_b[1:], time_b[-1:]]) - time_b))
            )
            text += f"[green]Start time set to {args.ts:.2f}[/] s\n"
        else:
            # Handle empty array case
            total_bytes = 0
            text += f"[red]Warning: No data after start time {args.ts:.2f}[/] s\n"
    else:
        if len(time_b) > 0:
            text += f"Start time: [cyan]{time_b[0]:.2f}[/] s \n"
        else:
            text += f"[red]Warning: No data available[/]\n"

    # shorten data according to end time
    if args.te:
        indices = np.where(time_b <= args.te)
        time_b = time_b[indices]
        bandwidth = bandwidth[indices]
        total_bytes = int(
            np.sum(bandwidth * (np.concatenate([time_b[1:], time_b[-1:]]) - time_b))
        )
        text += f"[green]End time set to {args.te:.2f}[/] s\n"
    else:
        if len(time_b) > 0:
            text += f"End time: [cyan]{time_b[-1]:.2f}[/] s\n"
        else:
            text += f"[red]Warning: No data in time window[/]\n"

    # ignored bytes
    ignored_bytes = ignored_bytes - total_bytes
    if ignored_bytes < 0:
        ignored_bytes = 0
    text += f"Total bytes: [cyan]{total_bytes:.2e} bytes[/]\n"
    text += f"Ignored bytes: [cyan]{ignored_bytes:.2e} bytes[/]\n"

    return bandwidth, time_b, text
