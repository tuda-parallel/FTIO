"""
This module provides functionality for managing data staging in GekkoFS using Cargo. It includes
adaptive triggering based on predictions, environment setup for Cargo operations, and efficient
data transfer mechanisms.

Author: Ahmad Tarraf
Copyright (c) 2025 TU Darmstadt, Germany
Date: Mar 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Queue

import numpy as np

from ftio.api.gekkoFs.gekko_helper import preloaded_call
from ftio.api.gekkoFs.posix_control import move_files_os
from ftio.freq.helper import MyConsole
from ftio.parse.args import parse_args

CONSOLE = MyConsole()
CONSOLE.set(True)


def stage_files(args: argparse.Namespace, latest_prediction: dict) -> None:
    """
    Stages the files based on the provided prediction.

    Args:
        args (Namespace): Parsed command line arguments.
        latest_prediction (dict): Result from FTIO containing prediction details.
    """
    period = 1 / latest_prediction["freq"] if latest_prediction["freq"] > 0 else 0
    text = f"frequency: {latest_prediction['freq']}\nperiod: {period} \nconfidence: {latest_prediction['conf']}\nprobability: {latest_prediction['probability']}\n"
    CONSOLE.print(f"[bold green][Trigger][/][green]{text}\n")
    if args.cargo:
        move_files_cargo(args, period=period)
    else:  # standard move
        move_files_os(args, period=period)


def setup_cargo(args: argparse.Namespace) -> None:
    """
    Sets up the cargo environment for staging data using the provided arguments.

    Args:
        args (Namespace): A namespace object containing the following attributes:
            - cargo (bool): Flag indicating whether to perform cargo setup.
            - cargo_bin (str): Path to the cargo binary directory.
            - cargo_server (str): Address of the cargo server.
            - stage_out_path (str): Path for stage-out operations.
    """
    if args.cargo:
        # 1. Perform stage in outside FTIO with cpp
        # 2. Setup für Cargo Stage-out für cargo_ftio
        call = f"{args.cargo_bin}/cargo_ftio --server {args.cargo_server} --run"
        CONSOLE.print("\n[bold green][Init][/][green]" + call + "\n")
        os.system(call)

        # 3. tells cargo that for all next cargo_ftio calls use the cpp
        # input is relative from GekokFS
        call = f"{args.cargo_bin}/ccp --server {args.cargo_server} --input / --output {args.stage_out_path} --if gekkofs --of parallel"
        CONSOLE.print("\n[bold green][Init][/][green]" + call + "\n")
        os.system(call)
        # 4. trigger with the thread
        # 5. Do a stage out outside FTIO with cargo_ftio --run


def trigger_flush(sync_trigger: Queue, args: argparse.Namespace) -> None:
    """
    Sends cargo calls by extracting predictions from `sync_trigger` and examining them.

    Args:
        sync_trigger (Queue): A queue from multiprocessing.Manager containing predictions.
        args (Namespace): Parsed command line arguments.
    """
    if "flush" in args.strategy:
        strategy_avoid_interference(sync_trigger, args)
    elif "job_end" in args.strategy:
        pass
    elif "buffer_size" in args.strategy:
        pass
    else:
        raise ValueError("Unknown strategy")


def strategy_job_end(sync_trigger: Queue, args: argparse.Namespace) -> None:
    with ProcessPoolExecutor(max_workers=2) as executor:
        while True:
            try:
                if not sync_trigger.empty():
                    latest_prediction = sync_trigger.get()
                    deadline = args.job_time
                    if not np.isnan(latest_prediction["freq"]):
                        t = time.time() - latest_prediction["t_wait"]
                        gkfs_elapsed_time = latest_prediction["t_flush"] + t
                        next_flush_time = latest_prediction["t_end"] + 1 / (
                            latest_prediction["freq"] * 2
                        )
                        # 1) do we have enough time to flush?
                        remaining_time = 0.8 * deadline - (
                            gkfs_elapsed_time + next_flush_time
                        )
                        # 2)
                        t_s = latest_prediction["t_start"]
                        t_e = latest_prediction["t_end"]
                        n_phases = (t_e - t_s) * latest_prediction["freq"]
                        avr_time_per_phase = gkfs_elapsed_time / n_phases

                        if (
                            remaining_time <= 0
                            or gkfs_elapsed_time + avr_time_per_phase > deadline
                        ):
                            _ = executor.submit(stage_files, args, latest_prediction)
                time.sleep(0.01)
            except KeyboardInterrupt:
                exit()


def strategy_buffer_size(sync_trigger: Queue, args: argparse.Namespace) -> None:
    with ProcessPoolExecutor(max_workers=2) as executor:
        while True:
            try:
                if not sync_trigger.empty():
                    latest_prediction = sync_trigger.get()
                    size_call = f"du -sb {args.gkfs_mntdir}/*"
                    output = preloaded_call(args, size_call)
                    buffer_occupation = sum(
                        int(line.split()[0]) for line in output.splitlines()
                    )
                    if not np.isnan(latest_prediction["freq"]):
                        total_size = latest_prediction["total_bytes"]
                        t_s = latest_prediction["t_start"]
                        t_e = latest_prediction["t_end"]
                        n_phases = (t_e - t_s) * latest_prediction["freq"]
                        avr_bytes = int(total_size / float(n_phases))
                        if avr_bytes + buffer_occupation > args.buffer_size:
                            _ = executor.submit(stage_files, args, latest_prediction)
                time.sleep(0.01)
            except KeyboardInterrupt:
                exit()


def strategy_avoid_interference(sync_trigger: Queue, args: argparse.Namespace) -> None:
    """
    Sends cargo calls by extracting predictions from `sync_trigger` and examining them.

    Args:
        sync_trigger (Queue): A queue from multiprocessing.Manager containing predictions.
        args (Namespace): Parsed command line arguments.
    """

    # if set to skip, the trigger will skip the latest_prediction if a new one is available
    # if set to cancel, the latest latest_prediction is canceled
    # if empty, cargo is triggered with each latest_prediction
    # adaptive = ""
    # adaptive = "skip"
    adaptive = "cancel"
    not_in_time = 0
    skipped = 0
    cancel_counter = 0
    with ProcessPoolExecutor(max_workers=5) as executor:
        while True:
            try:
                if not sync_trigger.empty():
                    latest_prediction = sync_trigger.get()
                    t = time.time() - latest_prediction["t_wait"]  # time waiting so far
                    # CONSOLE.print(f"[bold green][Trigger] queue wait time = {t:.3f} s[/]\n")
                    if not np.isnan(latest_prediction["freq"]):
                        # ? 1) Find estimated number of phases and skip in case less than 1
                        # n_phases = (latest_prediction['t_end']- latest_prediction['t_start'])*latest_prediction['freq']
                        # if n_phases <= 1:
                        #     CONSOLE.print(f"[bold green][Trigger] Skipping this latest_prediction[/]\n")
                        #     continue

                        # ? 2) Time analysis to find the right instance when to send the data
                        target_time = latest_prediction["t_end"] + 1 / (
                            latest_prediction["freq"] * 2
                        )
                        gkfs_elapsed_time = (
                            latest_prediction["t_flush"] + t
                        )  # t is the waiting time in this function. t_flush contains the overhead of ftio + when the data was flushed from gekko
                        remaining_time = target_time - gkfs_elapsed_time
                        CONSOLE.print(
                            f"[bold green][Trigger {latest_prediction['source']}][/][green]\n"
                            f"Probability   : {latest_prediction['probability']*100:.0f}%\n"
                            f"Elapsed time  : {gkfs_elapsed_time:.3f} s\n"
                            f"Target time   : {target_time:.3f} s\n"
                            f"--> trigger in {remaining_time:.3f} s[/]\n"
                        )
                        if remaining_time > 0:
                            countdown = time.time() + remaining_time
                            # wait till the time elapses:
                            while time.time() < countdown:
                                # ? 3) While waiting, cancel new latest_prediction is available
                                condition = True
                                if adaptive:
                                    if not sync_trigger.empty():
                                        if "skip" in adaptive:
                                            skipped += 1
                                            condition = False
                                            # if skipped more than 2, force flushing
                                            if skipped >= 2:
                                                if not condition:
                                                    condition = True  # continue waiting until the time ends
                                                    CONSOLE.print(
                                                        f"[bold green][Trigger][/][yellow]Too many skips, staging data out in {time.time() < countdown} s[/]\n"
                                                    )
                                            else:
                                                CONSOLE.print(
                                                    f"[bold green][Trigger][/][yellow]Skipping, new latest_prediction is ready (skipped: {skipped})[/]\n"
                                                )
                                                break  # no need to wait
                                    else:
                                        # remove the new latest_prediction from the queue
                                        _ = sync_trigger.get()
                                        # used only for counting
                                        cancel_counter += 1
                                        CONSOLE.print(
                                            f"[bold green][Trigger][/][yellow]Canceled incoming latest_prediction {cancel_counter}[/]\n"
                                        )
                                time.sleep(0.01)

                            if condition and latest_prediction["probability"] > 0.5:
                                _ = executor.submit(stage_files, args, latest_prediction)
                                # stage_files(args, latest_prediction)
                                skipped = 0
                                cancel_counter = 0
                            else:
                                # TODO: skip only of the predictions overlap
                                pass

                        else:
                            not_in_time += 1
                            if not_in_time == 3:
                                CONSOLE.print(
                                    "[bold green][Trigger][/][yellow]Not in time 3 times, triggering flush[/]\n"
                                )
                                stage_files(args, latest_prediction)
                                not_in_time = 0
                            else:
                                CONSOLE.print(
                                    "[bold green][Trigger][/][yellow]Skipping, not in time[/]\n"
                                )

                time.sleep(0.01)
            except KeyboardInterrupt:
                exit()


def move_files_cargo(args: argparse.Namespace, period: float = 0) -> None:
    """
    Moves files using Cargo.

    Args:
        args (Namespace): Parsed command line arguments.
        period (float, optional): Time period for file modification checks. Defaults to 0.

    """
    if period != 0 and args.ignore_mtime:
        # threshold = period / 2  # the io took half the time
        threshold = period / 2  # the io took half the time
        threshold = max(threshold, 5)
        call = f"{args.cargo_bin}/cargo_ftio --server {args.cargo_server} --run --mtime {int(threshold)}"
    else:
        call = f"{args.cargo_bin}/cargo_ftio --server {args.cargo_server} --run"

    CONSOLE.print(f"[bold green][Trigger][/][green]{call}")
    os.system(call)


def parse_args_data_stager(
    args: list[str], parse_args_ftio: bool = False
) -> tuple[argparse.Namespace, list[str]]:
    """
    Parses command-line arguments for Cargo and optionally FTIO.

    Args:
        args (list[str]): List of command-line arguments. Use '--' to separate Cargo-specific
            arguments from FTIO-specific arguments.
        parse_args_ftio (bool): If True, parses FTIO-specific arguments in addition to Cargo arguments.

    Returns:
        tuple[argparse.Namespace, list[str]]: A tuple containing:
            - Parsed arguments as a Namespace object with merged Cargo and FTIO attributes.
            - Remaining FTIO-specific arguments as a list of strings (if parse_args_ftio is True).
    """
    if "--" in args:
        split_index = args.index("--")
        cargo_specific_args = args[0:split_index]
        ftio_args = args[split_index + 1 :]
    else:
        cargo_specific_args = args
        ftio_args = []

    parser = argparse.ArgumentParser(
        description="Data staging arguments",
        prog="predictor_jit",
        epilog="Use '--' to separate cargo arguments from the ftio arguments.\n"
        "Example:\n"
        "predictor_jit {cargo_args} -- {ftio_args}..",
        add_help=True,  # Enable help for this parser
    )

    # cargo flags
    parser.add_argument(
        "--cargo",
        "--cargo",
        dest="cargo",
        action="store_true",
        help="Uses Cargo if provided to move data",
        default=False,
    )
    parser.add_argument(
        "--cargo_bin",
        "--cargo_bin",
        dest="cargo_bin",
        type=str,
        help="Location of Cargo cli",
        default="/lustre/project/nhr-admire/vef/cargo/build/cli",
    )
    parser.add_argument(
        "--cargo_server",
        "--cargo_server",
        dest="cargo_server",
        type=str,
        help="Address and port where cargo is running",
        default="ofi+sockets://127.0.0.1:62000",
    )
    parser.add_argument(
        "--adaptive",
        dest="adaptive",
        help="Adaptive flag for flushing",
        default="cancel",
        choices={"skip", "cancel", ""},
    )
    parser.add_argument(
        "--ignore_mtime",
        dest="ignore_mtime",
        action="store_true",
        help="Ignores mtime for files when flushing",
        default=False,
    )
    parser.add_argument(
        "-t",
        "--mtime-threshold",
        dest="mtime_threshold",
        type=float,
        default=1,
        help="Minimum age (in seconds) of a file's modification time to be considered for transfer (default=1 second).",
    )
    parser.add_argument(
        "--stage_out_path",
        dest="stage_out_path",
        type=str,
        help="Cargo stage out path",
        default="/lustre/project/nhr-admire/tarraf/stage-out",
    )
    parser.add_argument(
        "--parallel_move_threads",
        dest="parallel_move_threads",
        type=int,
        help="If set, flushes files in parallel",
        default=1,
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Debug flag",
        default=False,
    )
    # JIT flags without cargo
    parser.add_argument(
        "--stage_in_path",
        dest="stage_in_path",
        type=str,
        help="Cargo stage int path",
        default="/lustre/project/nhr-admire/tarraf/stage-in",
    )
    parser.add_argument(
        "--regex",
        dest="regex",
        type=str,
        default=None,
        help="Files that match the regex expression are ignored during stage out",
    )
    parser.add_argument(
        "--ld_preload",
        type=str,
        default=None,
        help="LD_PRELOAD call to GekkoFs file.",
    )
    parser.add_argument(
        "--host_file", type=str, default=None, help="Hostfile for GekkoFs."
    )
    parser.add_argument(
        "--gkfs_mntdir",
        type=str,
        default=None,
        help="Mount directory for GekkoFs.",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["flush", "job_end", "buffer_size"],
        default="flush",
        help="Flushing strategy: 'flush' (immediate), 'job_end' (wait until job finishes), or 'buffer_size' (flush after reaching given size).",
    )
    parser.add_argument(
        "--job_time",
        type=int,
        default=0,
        help="Time in seconds required for strategy 'job_end'.",
    )
    parser.add_argument(
        "--buffer_size",
        type=int,
        default=0,
        help="Buffer size in bytes required for strategy 'buffer_size'.",
    )
    parser.add_argument(
        "--flush_call",
        type=str,
        choices=["cp", "tar"],
        default="cp",
        help="Flushing method: 'cp' to copy files or 'tar' to compress them.",
    )

    # Parse the arguments
    tmp_args = parse_args(ftio_args, "ftio JIT")

    # print cargo help
    if (
        "-h" in ftio_args
        or "--help" in ftio_args
        or "--help" in cargo_specific_args
        or "-h" in cargo_specific_args
    ):
        parser.print_help()
        tmp_args = parse_args(["-h"], "ftio JIT")
        sys.exit(0)

    cargo_args = parser.parse_args(cargo_specific_args)

    # Merge
    cargo_args = argparse.Namespace(**vars(cargo_args), **vars(tmp_args))

    if parse_args_ftio:
        ftio_args = tmp_args

    return cargo_args, ftio_args
