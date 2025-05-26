"""Function to plot the bandwidth from the JIT"""

import json
import os
import argparse
import plotly.graph_objs as go
import plotly.io as pio
import numpy as np
from rich.console import Console
from rich.panel import Panel

from ftio.plot.units import set_unit
from ftio.plot.helper import format_plot_and_ticks


def load_json_and_plot(filenames):
    """Loads a JSON file and plots it

    Args:
        filenames (str): absolute path with filename
    """
    # Get the current directory
    current_directory = os.getcwd()

    # Create a list to hold traces
    traces = []
    unit = "MB"
    order = 1e-6

    for filename in filenames:
        # Define the path to the JSON file
        json_file_path = os.path.join(current_directory, filename)

        # Load the JSON file
        with open(json_file_path, "r") as json_file:
            data = json.load(json_file)

        # Extract arrays from the JSON data
        b = np.array(data.get("b", []))
        t = np.array(data.get("t", []))

        # If both b and t are empty, proceed to extract from sync types
        if b.size == 0 and t.size == 0:
            # Search for the 'bandwidth' key in all sync types (write_sync, read_sync, etc.)
            for sync_type, sync_data in data.items():
                if "bandwidth" in sync_data:
                    print(f"found type:{sync_type}")
                    b = np.array(sync_data["bandwidth"].get("b_overlap_avr", []))
                    t = np.array(sync_data["bandwidth"].get("t_overlap", []))
                    break

        if filenames.index(filename) == 0:
            unit, order = set_unit(b)

        plot_bar_with_rich(t, b)

        # Create a scatter plot trace of b against t
        trace = go.Scatter(
            x=t,
            y=b * order,
            mode="lines+markers",
            line={"shape": "hv"},
            fill="tozeroy",
            name=filename,  # Set the legend name to the filename
        )

        # Add the trace to the list
        traces.append(trace)

    # Create a figure and add all traces
    fig = go.Figure(data=traces)

    # Update layout for better visualization
    fig.update_layout(
        title="Stage-out Data",
        xaxis_title="Time (s)",
        yaxis_title=f"Bandwidth ({unit})",
        showlegend=True,
    )
    fig = format_plot_and_ticks(fig, font_size=27, n_ticks=10)

    # Show the plot
    pio.show(fig)


def non_zero_mean(arr: np.ndarray):
    return np.mean(arr[np.nonzero(arr)]) if len(arr[np.nonzero(arr)]) > 0 else 0


def plot_bar_with_rich(
    x, y, max_height=10, terminal_width=None, width_percentage=0.95, func=non_zero_mean
):
    """
    Plots a bar chart using Rich library with dynamic width and properly scaled axis labels.

    Args:
        x (list or np.array): X-axis values.
        y (list or np.array): Y-axis values.
        max_height (int): Maximum height of the plot in characters.
        terminal_width (int, optional): Width of the terminal. If None, it will be auto-detected.
        width_percentage (float): Percentage of terminal width to use for the plot.
        func (function): for interpolating y in the interpolated x ranges (i.e., how to calculate a single
        representative y inside a x range)
    """

    console = Console()
    terminal_width = terminal_width or int(
        0.95 * console.size.width
    )  # Detect terminal width if not provided
    plot_width = int(terminal_width * (width_percentage - 0.05))  # Width for the plot area

    x = np.array(x[:])
    y = np.array(y[:])

    # Normalize y to fit within the height of the plot and determine y-axis units
    y_unit, y_scale = set_unit(y)
    y = y * y_scale
    y_min = min(y)
    y_max = max(y)
    y_scaled = np.interp(y, (y_min, y_max), (0, max_height)).astype(int)
    # Offset adjustment for the axis label indentation
    label_offset = len(f"{y_max:.2f}") + 1
    # print(f'y:{y}\n\nx:{x}\n\ny_scaled:{y_scaled}')

    # Normalize x to fit within the plot width
    x_min = min(x)
    x_max = max(x)
    x_scaled = np.interp(x, (x_min, x_max), (0, plot_width - label_offset - 1)).astype(int)

    # Create the plot grid ensuring no row exceeds plot width

    # Create the plot grid
    grid = []
    for level in range(max_height, -1, -1):
        row = []
        for i in range(plot_width - label_offset):
            idx = np.where(x_scaled == i)[0]
            # if i in x_scaled and y_scaled[idx[0]] >= level:
            if i in x_scaled and func(y_scaled[idx]) >= level:
                row.append("█")  # Bar character
            else:
                row.append(" ")
        grid.append("".join(row))

    # Create labels for start, middle, and end
    start_label = f"{x_min:.1f} sec"
    middle_label = f"{x[len(x) // 2]:.1f} sec"
    end_label = f"{x_max:.1f} sec"

    # Calculate label positions dynamically
    new_label_offset = len(f"{y_max:.2f} {y_unit}") + 2
    start_pos = 0
    middle_pos = (plot_width - new_label_offset) // 2 - len(middle_label) // 2
    end_pos = (plot_width - len(y_unit)) - len(end_label) - 1

    # Construct the label line
    label_line = [" "] * plot_width
    label_line[start_pos : start_pos + len(start_label)] = list(start_label)
    label_line[middle_pos : middle_pos + len(middle_label)] = list(middle_label)
    label_line[end_pos : end_pos + len(end_label)] = list(end_label)

    # Combine into final plot with 'Bytes' on y-axis
    plot_str = "\n".join(
        f"{y_min + (y_max - y_min) * (max_height - i) / max_height:{label_offset}.2f} {y_unit} │ {row}"
        for i, row in enumerate(grid)
    )

    # Adjust the alignment of the x-axis line and labels to account for the label_offset

    plot_str += f"\n{' ' * new_label_offset}└{'─' * (plot_width - len('└')-len(y_unit) -1)}>"  # Adjusted x-axis line
    plot_str += f"\n{' ' * new_label_offset}{''.join(label_line)}"  # Adjusted x-axis label
    plot_str = f" " * (label_offset + 2 + len(y_unit)) + "^\n" + plot_str

    # Create a panel with the plot
    panel = Panel(plot_str, title="Bandwidth Plot", border_style="bold cyan", width=terminal_width)

    # Display the plot
    console.print(panel)


def main():
    parser = argparse.ArgumentParser(
        description="Load JSON data from multiple files and plot bandwidth vs. time."
    )
    parser.add_argument(
        "filenames",
        type=str,
        nargs="+",
        # nargs='?',
        default=["bandwidth.json"],
        help="The paths to the JSON files to plot. Multiple files can be provided.",
    )
    args = parser.parse_args()
    load_json_and_plot(args.filenames)


if __name__ == "__main__":
    main()
