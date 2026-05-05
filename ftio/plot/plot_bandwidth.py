"""
Function to plot the bandwidth from the JIT

Author: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Version: 0.0.8
Date: Jan 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import argparse
import json
import os
from datetime import datetime

import numpy as np
import plotly.graph_objs as go
import plotly.io as pio
from rich.console import Console
from rich.panel import Panel

from ftio.plot.helper import format_plot_and_ticks
from ftio.plot.units import set_unit


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
        with open(json_file_path) as json_file:
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


def parse_flush_log(path: str) -> tuple[list[dict], list[dict]]:
    """Parse a flush.log file produced by the JIT staging layer.

    Returns:
        entries: dicts with ts, label, src, dst, copy_time, delete_time
        events:  dicts with ts, event (APP-START / APP-END strings)
    """
    entries: list[dict] = []
    events: list[dict] = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" | ", maxsplit=4)
                try:
                    ts = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
                second = parts[1].strip() if len(parts) > 1 else ""
                if second.startswith("APP-"):
                    events.append({"ts": ts, "event": second})
                elif len(parts) >= 5:
                    src_dst = parts[2].strip()
                    src = src_dst.split(" -> ")[0].strip()
                    dst = src_dst.split(" -> ")[1].strip() if " -> " in src_dst else ""
                    copy_time = float(
                        parts[3].replace("copy:", "").replace("s", "").strip()
                    )
                    delete_time = float(
                        parts[4].replace("delete:", "").replace("s", "").strip()
                    )
                    entries.append(
                        {
                            "ts": ts,
                            "label": second,
                            "src": src,
                            "dst": dst,
                            "copy_time": copy_time,
                            "delete_time": delete_time,
                        }
                    )
    except (FileNotFoundError, OSError):
        pass
    return entries, events


def plot_flush_log(flush_log_path: str, show: bool = True) -> go.Figure:
    """Gantt-style timeline of flush log entries.

    Each flushed file is shown as a horizontal bar whose width equals the
    total stage-out time (copy + delete).  Bars are coloured by trigger
    source (FTIO-trigger vs post-app).  APP-START / APP-END events appear
    as vertical dashed lines.

    Args:
        flush_log_path: path to the flush.log file written by the JIT layer.
        show: when True the figure is displayed in the browser.

    Returns:
        The Plotly Figure object (useful for embedding or saving).
    """
    entries, events = parse_flush_log(flush_log_path)
    if not entries and not events:
        print(f"No flush data found in {flush_log_path}")
        return go.Figure()

    all_ts = [e["ts"] for e in entries] + [ev["ts"] for ev in events]
    t0 = min(all_ts)

    def to_sec(ts: datetime) -> float:
        return (ts - t0).total_seconds()

    fig = go.Figure()

    group_cfg = [
        ("FTIO-trigger", "#1f77b4"),
        ("post-app", "#ff7f0e"),
    ]
    for label, color in group_cfg:
        group = [e for e in entries if label in e["label"]]
        if not group:
            continue
        names = [os.path.basename(e["src"]) for e in group]
        starts = [to_sec(e["ts"]) for e in group]
        durations = [e["copy_time"] + e["delete_time"] for e in group]
        hovers = [
            f"File: {e['src']}<br>"
            f"Copy: {e['copy_time']:.3f} s | Delete: {e['delete_time']:.3f} s"
            for e in group
        ]
        fig.add_trace(
            go.Bar(
                x=durations,
                y=names,
                orientation="h",
                base=starts,
                name=label,
                marker_color=color,
                hovertext=hovers,
                hoverinfo="text+y",
                opacity=0.8,
            )
        )

    for ev in events:
        t = to_sec(ev["ts"])
        is_start = "START" in ev["event"]
        fig.add_vline(
            x=t,
            line_dash="dash",
            line_color="green" if is_start else "red",
            annotation_text=ev["event"],
            annotation_position="top right" if is_start else "top left",
        )

    fig.update_layout(
        title=f"Flush Timeline — {os.path.basename(flush_log_path)}",
        xaxis_title="Time from first event (s)",
        yaxis_title="File",
        barmode="overlay",
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )
    fig = format_plot_and_ticks(fig, font_size=18, n_ticks=10)

    if show:
        pio.show(fig)
    return fig


def non_zero_mean(arr: np.ndarray):
    return np.mean(arr[np.nonzero(arr)]) if len(arr[np.nonzero(arr)]) > 0 else 0


def plot_bar_with_rich(
    x,
    y,
    max_height=10,
    terminal_width=None,
    width_percentage=0.95,
    func=non_zero_mean,
    flush_log=None,
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
        representative y inside an x range)
    """

    console = Console()
    terminal_width = terminal_width or int(
        0.95 * console.size.width
    )  # Detect terminal width if not provided
    plot_width = int(
        terminal_width * (width_percentage - 0.05)
    )  # Width for the plot area

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
    x_scaled = np.interp(x, (x_min, x_max), (0, plot_width - label_offset - 1)).astype(
        int
    )

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
    plot_str += (
        f"\n{' ' * new_label_offset}{''.join(label_line)}"  # Adjusted x-axis label
    )
    plot_str = " " * (label_offset + 2 + len(y_unit)) + "^\n" + plot_str

    # Create a panel with the plot
    panel = Panel(
        plot_str,
        title="Bandwidth Plot",
        border_style="bold cyan",
        width=terminal_width,
    )

    # Display the plot
    console.print(panel)

    if flush_log and os.path.isfile(flush_log):
        entries, _ = parse_flush_log(flush_log)
        if entries:
            n_ftio = sum(1 for e in entries if "ftio" in e["label"].lower())
            n_post = len(entries) - n_ftio
            t_ftio = sum(
                e["copy_time"] + e["delete_time"]
                for e in entries
                if "ftio" in e["label"].lower()
            )
            t_post = sum(
                e["copy_time"] + e["delete_time"]
                for e in entries
                if "ftio" not in e["label"].lower()
            )
            summary = (
                f"Flushes: {n_ftio} FTIO-triggered ({t_ftio:.1f} s total), "
                f"{n_post} post-app ({t_post:.1f} s total)"
            )
            console.print(f"[dim]{summary}[/]")


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


def flush_main():
    parser = argparse.ArgumentParser(
        description="Plot a JIT flush.log as a Gantt-style timeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  plot_flush_log /path/to/logs/flush.log\n"
            "  plot_flush_log flush.log --save flush_timeline.html"
        ),
    )
    parser.add_argument(
        "flush_log",
        type=str,
        help="Path to the flush.log file produced by the JIT staging layer.",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        metavar="FILE",
        help="Save the figure to FILE (e.g. timeline.html) instead of opening a browser.",
    )
    args = parser.parse_args()
    fig = plot_flush_log(args.flush_log, show=args.save is None)
    if args.save and fig is not None:
        pio.write_html(fig, args.save)
        print(f"Saved to {args.save}")


if __name__ == "__main__":
    main()
