"""
This file provides functionality to plot results from JSON files
containing experimental data for JIT, JIT no FTIO, and Pure modes. It includes
functions to extract data, process it, and generate visualizations.

Author: Ahmad Tarraf
Copyright (c) 2025 TU Darmstadt, Germany
Date: Dec 2024

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import argparse
import json
import os
from pathlib import Path

from ftio.api.gekkoFs.jit.jit_result import JitResult


def plot_results(args):
    """
    Plot results from the given JSON files. If no filenames are provided,
    default data is used.

    Args:
        filenames (list): List of JSON file paths.
    """
    if not args:
        results = JitResult()
        # # run with x nodes  128 procs [jit | jit_no_ftio | pure] (now in old folder)
        # ################ Edit area ############################
        # title = "Nek5000 with 128 procs checkpointing every 10 steps with a total of 100 steps"
        # tmp_app = [207.3, 181.44, 181.56]
        # tmp_stage_out = [3.95,  17.68, 0]
        # tmp_stage_in =  [0.72,  0.75, 0]
        # results.add_experiment(tmp_app,tmp_stage_out,tmp_stage_in,"# 2")

        # # run with 3 nodes
        # tmp_app = [90.11, 84.81, 103]
        # tmp_stage_out = [2.26, 61.0, 0]
        # tmp_stage_in = [1.11, 1.11, 0]
        # results.add_experiment(tmp_app,tmp_stage_out,tmp_stage_in,"# 3")

        # tmp_app = [70.53, 72.71, 80.21]
        # tmp_stage_out = [1.891,9.430, 0]
        # tmp_stage_in = [1.149, 1.145, 0]
        # results.add_experiment(tmp_app,tmp_stage_out,tmp_stage_in,"# 4")

        # run with x nodes 32 procs [jit | jit_no_ftio | pure] (now in old folder)
        ################ Edit area ############################
        # # run with 3 nodes
        # tmp_app       = [ 157.8 , 156.51 , 160 ]
        # tmp_stage_out = [ 1.041 , 1.04 ,  0]
        # tmp_stage_in  = [ 1.099 ,  1.09,  0]
        # add_experiment(data,tmp_app,tmp_stage_out,tmp_stage_in,"# 3")

        # tmp_app       = [ 114.72,122.07  ,  130.95]
        # tmp_stage_out = [ 1.04, 1.03 ,  0]
        # tmp_stage_in  = [ 1.11, 1.83  ,  0]
        # add_experiment(data,tmp_app,tmp_stage_out,tmp_stage_in,"# 4")

        # tmp_app       = [ 97.11,106.31, 98.11]
        # tmp_stage_out = [ 1.05,1.12,0]
        # tmp_stage_in  = [ 1.13,1.12,0]
        # add_experiment(data,tmp_app,tmp_stage_out,tmp_stage_in,"# 5")

        # tmp_app       = [ 126.93,119.06, 93.27]
        # tmp_stage_out = [ 1.12,1.159,0]
        # tmp_stage_in  = [ 1.59,1.96,0]
        # add_experiment(data,tmp_app,tmp_stage_out,tmp_stage_in,"# 10")

        # tmp_app       = [ 182.58,174.67,90.64 ]
        # tmp_stage_out = [ 1.08,1.08,0]
        # tmp_stage_in  = [ 3.57,2.84,0]
        # add_experiment(data,tmp_app,tmp_stage_out,tmp_stage_in,"# 20")

        # title = "Nek5000 with 16 procs checkpointing every 10 steps with a total of 50 steps"
        # filename = "results_mogon/procs16_steps50_writeinterval10.json "

        title = "Nek5000 with 16 procs checkpointing every 5 steps with a total of 50 steps"
        filename = (
            "results_mogon/wacom++_app_proc_1_OMPthreads_64_12500000.json"
        )
        current_directory = os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(current_directory, filename)

        extract_and_plot(results, json_file_path, title)
    else:
        for filename in args.filenames:
            filename = str(Path(filename).resolve())
            print(f"Processing file: {filename}")
            results = JitResult()
            title = filename
            # title = ""
            current_directory = os.getcwd()
            json_file_path = os.path.join(current_directory, filename)
            extract_and_plot(
                results, json_file_path, title, no_diff=args.no_diff
            )


def extract_and_plot(
    results: JitResult, json_file_path: str, title: str, no_diff: bool = True
):
    """
    Extract data from a JSON file and plot the results.

    Args:
        results (JitResult): The JitResult object to store the extracted data.
        json_file_path (str): Path to the JSON file.
        title (str): Title for the plot.
        all (bool): Flag to control whether to call add_dict or add_all (default is False).
    """
    # Open the file and load the JSON data
    with open(json_file_path, "r") as json_file:
        data = json.load(json_file)

    # Sort the data by 'nodes'
    data = sorted(data, key=lambda x: x["nodes"])

    # Depending on the 'all' flag, process the data differently
    if no_diff:
        for d in data:
            results.add_dict(d)
        results.plot(title)
    else:
        for d in data:
            results.add_all(d)
        results.plot_all(title)


def main():
    """
    Main function to parse command-line arguments and plot results.
    """
    parser = argparse.ArgumentParser(
        description="Load JSON data from files and plot."
    )
    parser.add_argument(
        "filenames",
        type=str,
        nargs="*",  # '*' allows zero or more filenames
        default=[],
        help="The paths to the JSON file(s) to plot.",
    )
    # Boolean argument to determine whether to use the diff data
    parser.add_argument(
        "-n",
        "--no_diff",
        action="store_true",  # This stores True if the argument is provided, False otherwise
        help="Use the latest data based on the timestamp. Otherwise all data are plotted with error bars",
        default=False,
    )
    args = parser.parse_args()
    plot_results(args)


if __name__ == "__main__":
    main()
