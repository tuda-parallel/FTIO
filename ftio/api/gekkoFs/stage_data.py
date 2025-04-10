"""
This module provides functionality for managing data staging in GekkoFS using Cargo. It includes
adaptive triggering based on predictions, environment setup for Cargo operations, and efficient
data transfer mechanisms.

Author: Ahmad Tarraf  
Copyright (c) 2025 TU Darmstadt, Germany  
Date: January 2023

Licensed under the BSD 3-Clause License. 
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import os
import sys
import time
from multiprocessing import Queue
import numpy as np
import argparse
from ftio.parse.args import parse_args
from ftio.api.gekkoFs.posix_control import move_files_os
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()
CONSOLE.set(True)



def stage_files(args: argparse.Namespace, prediction: dict) -> None:
    """
    Stages the files based on the provided prediction.

    Args:
        args (Namespace): Parsed command line arguments.
        prediction (dict): Result from FTIO containing prediction details.
    """
    period = 1 / prediction["freq"] if prediction["freq"] > 0 else 0
    text = f"frequency: {prediction['freq']}\nperiod: {period} \nconfidence: {prediction['conf']}\nprobability: {prediction['probability']}\n"
    CONSOLE.print(f"[bold green][Trigger][/][green] {text}\n")
    if args.cargo:
        move_files_cargo(args)
    else:  # standard move
        move_files_os(args)

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


def trigger_cargo(sync_trigger: Queue, args: argparse.Namespace) -> None:
    """
    Sends cargo calls by extracting predictions from `sync_trigger` and examining them.

    Args:
        sync_trigger (Queue): A queue from multiprocessing.Manager containing predictions.
        args (Namespace): Parsed command line arguments.
    """
    
    # if set to skip, the trigger will skip the prediction if a new one is available
    # if set to cancel, the latest prediction is canaled
    # if empty, cargo is triggered with each prediction
    # adaptive = "" 
    # adaptive = "skip"
    adaptive = "cancel"

    not_in_time = 0
    skipped = 0
    while True:
        try:
            if not sync_trigger.empty():
                skip_flag = False
                prediction = sync_trigger.get()
                t = time.time() - prediction["t_wait"]  # time waiting so far
                # CONSOLE.print(f"[bold green][Trigger] queue wait time = {t:.3f} s[/]\n")
                if not np.isnan(prediction["freq"]):
                    # ? 1) Find estimated number of phases and skip in case less than 1
                    # n_phases = (prediction['t_end']- prediction['t_start'])*prediction['freq']
                    # if n_phases <= 1:
                    #     CONSOLE.print(f"[bold green][Trigger] Skipping this prediction[/]\n")
                    #     continue

                    # ? 2) Time analysis to find the right instance when to send the data
                    target_time = prediction["t_end"] + 1 / prediction["freq"]
                    gkfs_elapsed_time = (
                        prediction["t_flush"] + t
                    )  # t  is the waiting time in this function. t_flush contains the overhead of ftio + when the data was flushed from gekko
                    remaining_time = target_time - gkfs_elapsed_time
                    CONSOLE.print(
                        f"[bold green][Trigger {prediction['source']}][/][green]\n"
                        f"Probability   : {prediction['probability']*100:.0f}%\n"
                        f"Elapsed time  : {gkfs_elapsed_time:.3f} s\n"
                        f"Target time   : {target_time:.3f} s\n"
                        f"--> trigger in {remaining_time:.3f} s[/]\n"
                    )
                    if remaining_time > 0:
                        countdown = time.time() + remaining_time
                        # wait till the time elapses:
                        while time.time() < countdown:
                            pass
                        
                        # ? 3) Skip in case new prediction is available    

                        condition = True
                        if adaptive:
                            if not sync_trigger.empty():
                                if "skip" in adaptive:
                                    skip_flag = True
                                    skipped += 1
                                condition = (not skip_flag or skipped == 2)
                            else:
                                # remove the new prediction from the queue
                                _ = sync_trigger.get()

                        if condition and prediction["probability"] > 0.5: 
                            stage_files(args, prediction)
                            skipped = 0
                        else:
                            # TODO: skip only of the predictions overlap
                            CONSOLE.print(
                                f"[bold green][Trigger][/][yellow] Skipping, new prediction is ready (skipped: {skipped})[/]\n"
                            )

                    else:
                        not_in_time += 1
                        if not_in_time == 3:
                            CONSOLE.print(
                                "[bold green][Trigger][/][yellow] Not in time 3 times, triggering flush[/]\n"
                            )
                            stage_files(args, prediction)
                            not_in_time = 0
                        else:
                            CONSOLE.print(
                                "[bold green][Trigger][/][yellow] Skipping, not in time[/]\n"
                            )

            time.sleep(0.01)
        except KeyboardInterrupt:
            exit()


def move_files_cargo(args: argparse.Namespace) -> None:
    """
    Moves files using Cargo.

    Args:
        args (Namespace): Parsed command line arguments.
    """
    call = f"{args.cargo_bin}/cargo_ftio --server {args.cargo_server} --run"
    CONSOLE.print(f"[bold green][Trigger][/][green] {call}")
    os.system(call)


def parse_args_cargo(
    args: list[str],
    parse_args_ftio: bool = False
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
    if '--' in args:
        split_index = args.index('--')
        cargo_specific_args = args[0:split_index]
        ftio_args = args[split_index + 1:]
    else:
        cargo_specific_args = args
        ftio_args = []

    parser = argparse.ArgumentParser(
        description='Data staging arguments',
        prog='predictor_jit',
        epilog="Use '--' to separate cargo arguments from the ftio arguments.\n"
            "Example:\n"
            "predictor_jit {cargo_args} -- {ftio_args}..",
        add_help=True  # Enable help for this parser
    )

    # cargo flags
    parser.add_argument('--cargo', '--cargo', dest='cargo', action = 'store_true', help = 'Uses Cargo if provided to move data')
    parser.set_defaults(cargo =  False)
    parser.add_argument('--cargo_bin', '--cargo_bin', dest='cargo_bin', type = str, help = 'Location of Cargo cli')
    parser.set_defaults(cargo_bin = '/lustre/project/nhr-admire/vef/cargo/build/cli')
    parser.add_argument('--cargo_server', '--cargo_server', dest='cargo_server', type = str, help = 'Address and port where cargo is running')
    parser.set_defaults(cargo_server = 'ofi+sockets://127.0.0.1:62000')
    parser.add_argument('--stage_out_path', '--stage_out_path', dest='stage_out_path', type = str, help = 'Cargo stage out path')
    parser.set_defaults(stage_out_path = '/lustre/project/nhr-admire/tarraf/stage-out')
    # JIT flags without cargo
    parser.add_argument('--stage_in_path', '--stage_in_path', dest='stage_in_path', type = str, help = 'Cargo stage int path')
    parser.set_defaults(stage_in_path = '/lustre/project/nhr-admire/tarraf/stage-in')
    parser.add_argument('--regex', '--regex', dest='regex', type = str, default=None, help = 'Files that match the regex expression are ignored during stage out')
    
    parser.add_argument('-T', '--mtime-threshold', dest='mtime_threshold', type=float, default=1,  help='Minimum age (in seconds) of a file\'s modification time to be considered for transfer (default=1 second).')

            
    parser.add_argument("--ld_preload", type=str, default=None, help="LD_PRELOAD call to GekkoFs file.")
    parser.add_argument("--host_file", type=str, default=None,  help="Hostfile for GekkoFs.")
    parser.add_argument("--gkfs_mntdir", type=str, default=None,  help="Mount directory for GekkoFs.")

    # Parse the arguments
    tmp_args = parse_args(ftio_args,'ftio JIT')
    
    # print cargo help
    if '-h' in ftio_args or '--help' in ftio_args or '--help' in cargo_specific_args or '-h' in cargo_specific_args:
        parser.print_help()
        tmp_args = parse_args(['-h'],'ftio JIT')
        sys.exit(0)

    cargo_args = parser.parse_args(cargo_specific_args)

    # Merge
    cargo_args = argparse.Namespace(**vars(cargo_args), **vars(tmp_args))

    if parse_args_ftio:
        ftio_args = tmp_args


    return cargo_args, ftio_args