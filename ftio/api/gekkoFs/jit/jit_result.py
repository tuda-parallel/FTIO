"""
This file provides the `JitResult` class for managing and visualizing experimental data 
related to application times, stage out times, and stage in times. It includes methods 
for adding experiments, processing data from dictionaries, sorting data based on timestamps, 
and generating plots for analysis.

Author: Ahmad Tarraf  
Copyright (c) 2025 TU Darmstadt, Germany  
Date: Mar 2025

Licensed under the BSD 3-Clause License. 
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import numpy as np
import plotly.graph_objects as go
from ftio.plot.helper import format_plot_and_ticks

class JitResult:
    def __init__(self) -> None:
        """
        Initialize a JitResult object to store experimental data.
        """
        self.app       = []
        self.stage_out = []
        self.stage_in  = []
        self.node = []
        self.app_stats = {}
        self.stage_out_stats = {}
        self.stage_in_stats = {}

    def add_experiment(self,tmp_app:list[float],tmp_stage_out:list[float],tmp_stage_in:list[float],run:str):
        """
        Add an experiment's data to the JitResult object.

        Args:
            tmp_app (list[float]): Application times.
            tmp_stage_out (list[float]): Stage out times.
            tmp_stage_in (list[float]): Stage in times.
            run (str): Identifier for the experiment run.
        """
        self.app = add_mode(self.app,tmp_app)
        self.stage_out = add_mode(self.stage_out,tmp_stage_out)
        self.stage_in = add_mode(self.stage_in,tmp_stage_in)
        self.node.append(run)

    def add_experiment_with_stats(self, tmp_app: list[float], tmp_stage_out: list[float], tmp_stage_in: list[float], run: str, app_stats: dict, stage_out_stats: dict, stage_in_stats: dict):
        """
        Add an experiment's data to the JitResult object, including stats (min, max, mean).

        Args:
            tmp_app (list[float]): Application times.
            tmp_stage_out (list[float]): Stage out times.
            tmp_stage_in (list[float]): Stage in times.
            run (str): Identifier for the experiment run.
            app_stats (dict): Dictionary containing min, max, and mean stats for 'app'.
            stage_out_stats (dict): Dictionary containing min, max, and mean stats for 'stage_out'.
            stage_in_stats (dict): Dictionary containing min, max, and mean stats for 'stage_in'.
        """
        # First, use add_experiment to handle the raw data
        self.add_experiment(tmp_app, tmp_stage_out, tmp_stage_in, run)

        # Now, store the statistics
        self.app_stats[run] = app_stats
        self.stage_out_stats[run] = stage_out_stats
        self.stage_in_stats[run] = stage_in_stats


    def add_dict(self, data_list: list[dict], get_latest_timestamp: bool = True):
        """
        Add data from a dictionary to the JitResult object, optionally using the latest data based on the timestamp.

        Args:
            data_list (list[dict]): List of dictionaries containing experimental data.
            get_latest_timestamp (bool): Whether to use the latest entry based on the timestamp (default is False).
        """
        tmp_app = [0.0, 0.0, 0.0]
        tmp_stage_out = [0.0, 0.0, 0.0]
        tmp_stage_in = [0.0, 0.0, 0.0]

        sorted_data = sort_data(data_list, get_latest_timestamp)

        # Now loop through the (possibly sorted) data
        for i in sorted_data:
            # Apply logic based on the mode
            if "F" in i["mode"]:
                index = 0
            elif "D" in i["mode"]:
                index = 1
            else:
                index = 2

            tmp_app[index] = i["app"]
            tmp_stage_out[index] = i["stage_out"]
            tmp_stage_in[index] = i["stage_in"]
        self.add_experiment(tmp_app,tmp_stage_out,tmp_stage_in,f"# {data_list["nodes"]}")


    def plot(self, title=""):
        """
        Plot the experimental data stored in the JitResult object.

        Args:
            title (str): Title for the plot.
        """
        # Sample data for the stacked plot
        categories = ['GLASS', 'Lustre & Gekko', 'Lustre']
        repeated_strings = [s for s in categories for _ in self.node]
        repeated_numbers = self.node * len(categories)
        categories = [repeated_strings, repeated_numbers]

        fig = go.Figure()

        fig.add_bar(x=categories, y=self.app, text=self.app, name="App")
        fig.add_bar(x=categories, y=self.stage_out, text=self.stage_out, name="Stage out")
        fig.add_bar(x=categories, y=self.stage_in, text=self.stage_in, name="Stage in")

        # Sum total
        total = list(np.round(np.array(self.app) + np.array(self.stage_out) + np.array(self.stage_in), 2))

        # Plot total
        fig.add_trace(go.Scatter(
            x=categories, 
            y=total,
            text=total,
            mode='text',
            textposition='top center',
            textfont=dict(size=18),  # Increased font size for total labels
            showlegend=False
        ))

        self.format_and_show(fig,title)


    def format_and_show(self,fig: go.Figure, title:str = "", barmode: str = "relative"):


        # Update text formatting
        fig.update_traces(
            textposition='inside',
            texttemplate="%{text:.2f}",
            textfont_size=18,  # Increased font size
            textangle=0,
            textfont=dict(color="white")
        )

        # Comment out to see all text
        fig.update_layout(uniformtext_minsize=10, uniformtext_mode='hide')


        # Update layout with larger font sizes
        fig.update_layout(
            yaxis_title="Time (s)",
            xaxis_title=f"Experimental Runs with # Nodes",
            showlegend=True,
            title=title,
            barmode= barmode,
            title_font_size=24,  # Increased title font size
            width=1000 + 100 * len(self.node),
            height=700,
            xaxis=dict(title_font=dict(size=24)),  # Increased x-axis title font size
            yaxis=dict(title_font=dict(size=24)),  # Increased y-axis title font size
            legend=dict(
                font=dict(size=20),  # Increased legend font size
                orientation="h",
                yanchor="bottom",
                y=0.9,
                xanchor="right",
                x=0.995
            )
        )

        
        format_plot_and_ticks(fig, x_minor=False,font_size=20)
        # Display the plot
        fig.show()

######################
# Add and plot all
#####################

    def add_all(self, data_list: list[dict], get_latest_timestamp: bool = True):
        """
        Add data from a dictionary to the JitResult object, optionally using the latest data based on the timestamp.

        Args:
            data_list (list[dict]): List of dictionaries containing experimental data.
            get_latest_timestamp (bool): Whether to use the latest entry based on the timestamp (default is False).
        """
        sorted_data = sort_data(data_list, get_latest_timestamp)

        # Add data per node configuration
        tmp_app = [0.0, 0.0, 0.0]
        tmp_stage_out = [0.0, 0.0, 0.0]
        tmp_stage_in = [0.0, 0.0, 0.0]

        # Track the entries for calculation
        app_values = {0: [], 1: [], 2: []}
        stage_out_values = {0: [], 1: [], 2: []}
        stage_in_values = {0: [], 1: [], 2: []}

        # Now loop through the (possibly sorted) data
        for i in sorted_data:
            # Apply logic based on the mode
            if "F" in i["mode"]:
                index = 0
            elif "D" in i["mode"]:
                index = 1
            else:
                index = 2

            # Add the **latest** data to the temporary lists
            tmp_app[index] = i["app"]
            tmp_stage_out[index] = i["stage_out"]
            tmp_stage_in[index] = i["stage_in"]

            # Collect all data points for min, max, mean calculations
            app_values[index].append(i["app"])
            stage_out_values[index].append(i["stage_out"])
            stage_in_values[index].append(i["stage_in"])

        # Calculate min, max, mean for each field and mode
        stats = {
            "app": {},
            "stage_out": {},
            "stage_in": {}
        }

        for index in range(3):
            stats["app"][index] = {
                "min": min(app_values[index]) if app_values[index] else 0,
                "max": max(app_values[index]) if app_values[index] else 0,
                "mean": np.mean(app_values[index]) if app_values[index] else 0
            }
            stats["stage_out"][index] = {
                "min": min(stage_out_values[index]) if stage_out_values[index] else 0,
                "max": max(stage_out_values[index]) if stage_out_values[index] else 0,
                "mean": np.mean(stage_out_values[index]) if stage_out_values[index] else 0
            }
            stats["stage_in"][index] = {
                "min": min(stage_in_values[index]) if stage_in_values[index] else 0,
                "max": max(stage_in_values[index]) if stage_in_values[index] else 0,
                "mean": np.mean(stage_in_values[index]) if stage_in_values[index] else 0
            }

        # Now call add_experiment, including stats
        self.add_experiment_with_stats(
            tmp_app, tmp_stage_out, tmp_stage_in,
            f"# {data_list['nodes']}",
            stats["app"], stats["stage_out"], stats["stage_in"]
        )


    def plot_all(self, title:str = ""):
        """
        Generate and plot all experimental data in a bar diagram with deviations (error bars).

        Args:
            title (str): Title for the plot.
        """
        categories = ['GLASS', 'Lustre & Gekko', 'Lustre']
        repeated_strings = [s for s in categories for _ in self.node]
        repeated_numbers = self.node * len(categories)
        categories = [repeated_strings, repeated_numbers]

        fig = go.Figure()
        app_values = []
        stage_out_values = []
        stage_in_values = []
        app_error_diff = []
        stage_out_error_diff = []
        stage_in_error_diff = []

        # Loop through all runs and plot the mean, min, and max for each mode (app, stage_out, stage_in)
        for index in range(3):  
            for run in self.node:
                # Get the statistics, defaulting to None if not available
                app_stats = self.app_stats.get(run, None)
                stage_out_stats = self.stage_out_stats.get(run, None)
                stage_in_stats = self.stage_in_stats.get(run, None)

                # Check if the statistics are available (otherwise skip this run or use default values)
                if app_stats is None or stage_out_stats is None or stage_in_stats is None:
                    continue  # Skip this run if any of the stats are missing

            # Extract the mean, min, and max values for each mode
                app_mean, app_min, app_max = app_stats.get(index).get("mean", 0.0), app_stats.get(index).get("min", 0.0), app_stats.get(index).get("max", 0.0)
                stage_out_mean, stage_out_min, stage_out_max = stage_out_stats.get(index).get("mean", 0.0), stage_out_stats.get(index).get("min", 0.0), stage_out_stats.get(index).get("max", 0.0)
                stage_in_mean, stage_in_min, stage_in_max = stage_in_stats.get(index).get("mean", 0.0), stage_in_stats.get(index).get("min", 0.0), stage_in_stats.get(index).get("max", 0.0)

                # Add these values to the lists
                app_values.append(app_mean)
                stage_out_values.append(stage_out_mean)
                stage_in_values.append(stage_in_mean)

                # Calculate error bars (min-max) and add them to the lists
                app_error_diff.append(app_max - app_min)
                stage_out_error_diff.append(stage_out_max - stage_out_min)
                stage_in_error_diff.append(stage_in_max - stage_in_min)

        # Plot app mean with min-max error bars
        fig.add_trace(go.Bar(
            x = [categories[0], categories[1]],
            y = app_values,  
            text = app_values,  
            name = f"App",
            error_y = dict(
                type ='data',
                array = app_error_diff
            )  # Min-max error bars
        ))

        # Plot stage out mean with min-max error bars
        fig.add_trace(go.Bar(
            x = [categories[0], categories[1]],
            y = stage_out_values,
            text = stage_out_values,
            name = f"Stage out",
            error_y = dict(
                type ='data',
                array = stage_out_error_diff
            )  # Min-max error bars
        ))

        # Plot stage in mean with min-max error bars
        fig.add_trace(go.Bar(
            x = [categories[0], categories[1]],
            y = stage_in_values,
            text = stage_in_values,
            name = f"Stage in",
            error_y = dict(
                type ='data',
                array = stage_in_error_diff
            )  # Min-max error bars
        ))


        self.format_and_show(fig,barmode="group",title=title)
        
#! helpers

def add_mode(list1, list2):
    """
    Combine two lists by interleaving elements from the first list with
    elements from the second list.

    Args:
        list1 (list): The first list.
        list2 (list): The second list.

    Returns:
        list: The combined list.
    """
    # Create a new list to store the result
    result = []
    step = int(len(list1)/3)
    
    # Iterate over the range of the lists' lengths
    for i in range(len(list2)):
        # Add the current element from each list    
        for j in range(step):
            result.append(list1[i*step+j])
        result.append(list2[i])
    
    return result


def sort_data(data_list: list[dict], get_latest_timestamp: bool = False):
    """
    Sorts a list of dictionaries based on timestamps and modes.
        data_list (list[dict]): A list of dictionaries containing data entries. 
                                Each dictionary should have a "data" key with a list of entries.
        get_latest_timestamp (bool): If True, sorts the data by timestamp in descending order 
                                    and keeps only the latest entry per unique combination of 
                                    "nodes" and "mode". If False, retains the original order.
    Returns:
        list[dict]: A sorted list of dictionaries. If `get_latest_timestamp` is True, the list 
                    contains the latest entries for each unique combination of "nodes" and "mode", 
                    along with entries without timestamps. Otherwise, the original order is preserved.
    """
    if get_latest_timestamp:
        # Separate entries with and without timestamps
        with_timestamp = [i for i in data_list["data"] if "timestamp" in i]
        without_timestamp = [i for i in data_list["data"] if "timestamp" not in i]

        # Sort the entries that have timestamps in descending order
        with_timestamp.sort(key=lambda x: x.get("timestamp", "0000-00-00 00:00:00"), reverse=True)

        # Now loop through the sorted data and update only the latest entry per mode
        nodes_data = {}  # A dictionary to track the latest data for each mode and nodes
        for i in with_timestamp:
            nodes = i["nodes"]
            mode = i["mode"]

            # If no entry exists for the current mode and nodes, add the entry
            if (nodes, mode) not in nodes_data:
                nodes_data[(nodes, mode)] = i
            else:
                # If an entry exists, check if the new entry is more recent
                existing_entry = nodes_data[(nodes, mode)]
                if i["timestamp"] > existing_entry["timestamp"]:
                    nodes_data[(nodes, mode)] = i

        # Combine the latest entries and those without timestamps
        sorted_data = list(nodes_data.values()) + without_timestamp
    else:
        # If not using timestamps, just use the original order
        sorted_data = data_list["data"]

    return sorted_data



