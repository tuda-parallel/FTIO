import json
import os
import plotly.graph_objs as go
import plotly.io as pio
import numpy as np
import argparse

from ftio.plot.units import set_unit
from ftio.plot.helper import format_plot_and_ticks

def load_json_and_plot(filenames):
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

        
        if filenames.index(filename) == 0:
            unit, order = set_unit(b)
        
        # Create a scatter plot trace of b against t
        trace = go.Scatter(
            x=t,
            y=b * order,
            mode='lines+markers',
            line={"shape": "hv"},
            fill="tozeroy",
            name=filename  # Set the legend name to the filename
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
        showlegend=True
    )
    fig = format_plot_and_ticks(fig)
    
    # Show the plot
    pio.show(fig)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load JSON data from multiple files and plot bandwidth vs. time.")
    parser.add_argument(
        'filenames',
        type=str,
        nargs='+',
        default=["bandwidth.json"],
        help="The paths to the JSON files to plot. Multiple files can be provided."
    )
    args = parser.parse_args()
    
    load_json_and_plot(args.filenames)
