"""
This module provides functionality for managing file operations in a GekkoFS environment.

The module leverages GekkoFS-specific environment variables and commands to manage file operations
efficiently. It also includes mechanisms for monitoring file modification times and ensuring
compatibility with GekkoFS libraries.

Author: Ahmad Tarraf
Copyright (c) 2025 TU Darmstadt, Germany
Date: January 2023

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import math
import os
import re
from argparse import Namespace
import subprocess
import time
from ftio.freq.helper import MyConsole
import mmap


CONSOLE = MyConsole()
CONSOLE.set(True)


def move_files_os(args: Namespace) -> None:
    """
    Moves files and directories from the source directory to the stage-out path.

    Args:
        args (Namespace): Parsed command line arguments.
    """
    CONSOLE.print("[bold green][Trigger][/][green] Moving files\n")
    # Ensure both source and destination directories exist

    # GekkoFs libc is currently not supported
    args.ld_preload = args.ld_preload.replace("libc_", "")
    # if not os.path.exists(args.gkfs_mntdir):
    #     print(f"Source directory '{args.stage_in_path}' does not exist.")
    #     return
    if not os.path.exists(args.stage_out_path):
        os.makedirs(args.stage_out_path)

    regex = None
    # Compile the regex pattern if provided
    if args.regex:
        CONSOLE.print(
            f"[bold green][Trigger][/][green] Using pattern: {args.regex}[/]\n"
        )
        regex = re.compile(args.regex)

    # Iterate over all items in the source directory
    files = get_files(args)

    # Ensure the target directory exists
    os.makedirs(args.stage_out_path, exist_ok=True)

    parallel = False

    if not parallel:
        for file_name in files:
            # print(f'regex: {regex}\nfile_name: {file_name}')
            # Check if the file matches the ignore pattern
            move_file(args, file_name, regex)
    else:
        with ProcessPoolExecutor(max_workers=5) as executor:
            # Submit tasks to the executor
            futures = {
                executor.submit(move_file, args, file_name, regex): i
                for i, file_name in enumerate(files)
            }

            # Process results as they complete
            for future in as_completed(futures):
                # index = futures[future]
                try:
                    future.result()
                except TimeoutError:
                    index = futures[future]
                    CONSOLE.print(f"[red bold] {files[index]} reached timeout")


def move_file(args: Namespace, file_name: str, regex: re.Pattern) -> None:
    """
    Stages out a single file if it matches the regex and meets modification time criteria.

    Args:
        args (Namespace): Parsed command line arguments.
        file_name (str): Name of the file to stage out.
        regex (re.Pattern): Compiled regex pattern to match files.
    """
    fast = False # fat copy still has an error with the preload
    if regex and regex.match(file_name):

        modification_time = time.time() - get_time(args, file_name)
        CONSOLE.print(f"File modified {modification_time:.2} seconds ago")
        if modification_time >= 2:
            CONSOLE.print(
                f"[bold green][Trigger][/][bold yellow] -- Moving file {file_name} --[/]\n"
            )
            os.makedirs(
                os.path.dirname(
                    file_name.replace(args.gkfs_mntdir, args.stage_out_path)
                ),
                exist_ok=True,
            )
            if fast:
                parallel_copy_file(args, file_name, threads=4)
            else:
                copy_file_and_unlink(args, file_name)
    else:
        print(f"Ignored: {file_name}")

    copy_file_and_unlink(args, file_name)


def copy_file_and_unlink(args: Namespace, file_name: str) -> None:
    preloaded_call(args, f"cp {file_name} {args.stage_out_path}")
    preloaded_call(args, f" unlink {file_name}")


def get_files(args: Namespace) -> list[str]:
    """
    Retrieves a list of files from the GekkoFS mount directory.

    Args:
        args (Namespace): Parsed command line arguments.

    Returns:
        list[str]: List of file paths.
    """
    files = preloaded_call(args, f"ls -R {args.gkfs_mntdir}")
    if files:
        files = files.splitlines()
        files = [f for f in files if "LIBGKFS" not in f]
        files = [f"{args.gkfs_mntdir}/{item}" for item in files if "." in item]

        return files
    else:
        return []


def get_time(args: Namespace, file_name: str) -> float:
    """
    Retrieves the last modification time of a file.

    Args:
        args (Namespace): Parsed command line arguments.
        file_name (str): Name of the file.

    Returns:
        float: Last modification time of the file.
    """
    output = preloaded_call(args, f"stat --format=%Y {file_name}")
    return float(output.strip())


def preloaded_call(args: Namespace, call: str) -> str:
    """
    Executes a shell command with GekkoFS preloaded environment variables.

    Args:
        args (Namespace): Parsed command line arguments.
        call (str): Shell command to execute.

    Returns:
        str: Output of the shell command.
    """
    call = f" LIBGKFS_HOSTS_FILE={args.host_file} LD_PRELOAD={args.ld_preload} {call}"
    return subprocess.check_output(call, shell=True, text=True)

def write_chunk(mmapped_file, dst, start, end, ld_preload=None):
    """Thread worker to write a chunk of the file to the destination."""
    # Ensure the LD_PRELOAD is set in the thread environment
    if ld_preload:
        os.environ["LD_PRELOAD"] = str(ld_preload)
    
    with open(dst, "r+b") as fdst:
        fdst.seek(start)
        fdst.write(mmapped_file[start:end])

def copy_metadata(src, dst, ld_preload=None):
    """Copy metadata (permissions and timestamps) from src to dst."""
    # Ensure the LD_PRELOAD is set in the current environment before performing metadata copy
    if ld_preload:
        os.environ["LD_PRELOAD"] = str(ld_preload)
    
    # Get the current metadata of the source file
    stat_info = os.stat(src)

    # Set the metadata on the destination file (timestamps and permissions)
    os.utime(
        dst, (stat_info.st_atime, stat_info.st_mtime)
    )  # Access and modification times
    os.chmod(dst, stat_info.st_mode)  # File permissions

def parallel_copy_file(args: Namespace, file_name, threads=4):
    """Copy a single file in parallel using multiple threads and optionally set LD_PRELOAD."""

    src = file_name
    dst = f"{args.stage_out_path}/{file_name}"  # Corrected dst path
    os.environ["LIBGKFS_HOSTS_FILE"] = str(args.host_file)
    os.environ["LD_PRELOAD"] = str(args.ld_preload) if args.ld_preload else ''

    # Get file size using open() to avoid potential issues with os.path.getsize()
    with open(src, 'rb') as fsrc:
        fsrc.seek(0, os.SEEK_END)
        file_size = fsrc.tell()  # This retrieves the file size

    # Memory-mapped file for reading (this will use LD_PRELOAD)
    with open(src, "rb") as fsrc:
        mmapped_file = mmap.mmap(fsrc.fileno(), 0, access=mmap.ACCESS_READ)

    # Create an empty file at destination with the same size
    with open(dst, "wb") as fdst:
        fdst.write(b"\0" * file_size)

    # Split file into chunks for each thread
    chunk_size = math.ceil(file_size / threads)
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for i in range(threads):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, file_size)
            futures.append(executor.submit(write_chunk, mmapped_file, dst, start, end, args.ld_preload))

        # Wait for all threads to finish
        for future in futures:
            future.result()

    # Copy metadata using os.utime and os.chmod (these system calls will be affected by LD_PRELOAD)
    copy_metadata(src, dst, args.ld_preload)
