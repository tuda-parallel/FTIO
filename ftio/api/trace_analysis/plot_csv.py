import pandas as pd
import argparse
import os  # To handle file path operations
import sys
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp

from ftio.api.trace_analysis.trace_analysis import reduce_to_max_conf


def main(argv=sys.argv):
    # Parse command-line arguments for file paths
    parser = argparse.ArgumentParser(description="Process some CSV files.")
    parser.add_argument(
        "file_paths", metavar="F", type=str, nargs="+", help="Paths to the CSV files"
    )
    args = parser.parse_args(argv)

    # List to store the DataFrames and filenames
    dataframes = []
    file_basenames = []

    # Read the CSV files into DataFrames and store their basenames
    for file_path in args.file_paths:
        df = pd.read_csv(file_path)
        basename = os.path.basename(file_path)  # Extract basename from file path
        basename = os.path.splitext(basename)[0]  # Remove extension
        df["Source File"] = basename  # Add a new column with the basename
        dataframes.append(df)
        file_basenames.append(basename)

    # Combine all DataFrames into a single DataFrame
    combined_df = pd.concat(dataframes, ignore_index=True)

    # Reshape the DataFrame to long format
    # Use "Source File" for the color coding and melt the DataFrame
    combined_df_long = pd.melt(
        combined_df, id_vars=["Source File"], var_name="Metric", value_name="Value"
    )
    single_plot(combined_df_long)
    sub_plots(combined_df_long, file_basenames)


def single_plot(df):
    # Use Plotly Express to create a box plot with color by filename
    fig = px.box(
        df,
        x="Metric",  # Column name for x-axis
        y="Value",  # Column name for y-axis
        color="Source File",  # Use the filename column for color
        title="Combined Box Plots by Metric",
        labels={"Metric": "Metric", "Value": "Values"},
    )  # Labels for the axes

    # Update layout
    fig.update_layout(
        boxmode="group",  # Group the boxes for better comparison
        height=600,
        width=1200,
        xaxis_title="Metric",
        yaxis_title="Values",
    )

    # Show the plot
    fig.show()


def sub_plots(df, file_basenames):
    # Get unique metrics
    metrics = df["Metric"].unique()
    num_metrics = len(metrics)

    # Create subplots with each row representing a metric
    fig = sp.make_subplots(
        rows=num_metrics, cols=1, subplot_titles=[f"{metric}" for metric in metrics]
    )

    # Loop through each metric and add a box plot to the corresponding subplot
    for i, metric in enumerate(metrics):
        # Filter data for the current metric
        metric_df = df[df["Metric"] == metric]

        # Create a box plot for the current metric
        box_trace = go.Box(
            x=metric_df["Source File"], y=metric_df["Value"], name=metric
        )
        # Clean the 'Value' column: Convert to numeric, coerce errors to NaN
        metric_df['Value'] = pd.to_numeric(metric_df['Value'], errors='coerce')
        # Drop rows where 'Value' could not be converted to numeric (i.e., NaN)
        metric_df = metric_df.dropna(subset=['Value'])

        # Add the box plot to the appropriate subplot
        fig.add_trace(box_trace, row=i + 1, col=1)
        for s in metric_df["Source File"].unique():
            fig.add_annotation(
                x=s,  # Use specific source file as x coordinate
                y=metric_df[metric_df["Source File"] == s]["Value"].max(),
                text=str(len(metric_df[metric_df["Source File"] == s]["Value"])),
                yshift=10,
                showarrow=False,
                row=i + 1,
                col=1
            )

    # Update layout for the entire figure
    fig.update_layout(
        title="Box Plots by Metric",
        height=400 * num_metrics,  # Adjust height for number of metrics
        width=1000,  # Adjust width for visibility
        xaxis_title="Source File",
        yaxis_title="Values",
        showlegend=False,  # Hide legend to reduce clutter
    )

    # Show the plot
    fig.show()


if __name__ == "__main__":
    main(sys.argv[1:])
