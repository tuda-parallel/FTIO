"""
This module provides functionality for managing file operations in a GekkoFS environment.

The module leverages GekkoFS-specific environment variables and commands to manage file operations
efficiently. It also includes mechanisms for monitoring file modification times and ensuring
compatibility with GekkoFS libraries.

Author: Ahmad Tarraf
Copyright (c) 2025 TU Darmstadt, Germany
Date: Apr 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import math
import os
import re
import argparse
import subprocess
import time
from ftio.api.gekkoFs.file_queue import FileQueue
from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.freq.helper import MyConsole
import mmap


CONSOLE = MyConsole()
CONSOLE.set(True)

files_in_progress = FileQueue()


def move_files_os(
    args: argparse.Namespace,
    parallel: bool = False,
    period:float = 0
) -> None:
    """
    Moves files and directories from the source directory to the stage-out path.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
        parallel (bool, optional): Whether to use parallel processing for file moving.
            modification time checks. Defaults to False.
        period (float, optional): Time period for file modification checks. Defaults to 0.
    """
    CONSOLE.print("[bold green][Trigger][/][green] Moving files\n")
    args.ld_preload = args.ld_preload.replace("libc_", "")
    if not os.path.exists(args.stage_out_path):
        os.makedirs(args.stage_out_path)

    if args.parallel_move:
        parallel = True

    regex = None
    # Compile the regex pattern if provided
    if args.regex:
        CONSOLE.print(
            f"[bold green][Trigger][/][green] Using pattern: {args.regex}[/]\n"
        )
        regex = re.compile(args.regex)

    # Iterate over all items in the source directory
    files = get_files(args)
    if args.debug:
        f"[bold green][Trigger][/][green] Files are:\n {files}[/]\n"

    # Ensure the target directory exists
    os.makedirs(args.stage_out_path, exist_ok=True)
    if not parallel:
        for file_name in files:
            if regex and regex.match(file_name):
                if not files_in_progress.in_progress(file_name):
                    files_in_progress.put(file_name)
                    move_file(args, file_name, period)
                    files_in_progress.mark_done(file_name)
                else:
                    if args.debug:
                        CONSOLE.print(
                            f"[bold green][Trigger][/]: already moving {file_name}"
                        )

            else:
                if args.debug:
                    CONSOLE.print(f"[bold green][Trigger][/]:  Ignored {file_name}")
    else:
        futures = {}
        with ProcessPoolExecutor(max_workers=5) as executor:
            # Submit tasks to the executor
            for i, file_name in enumerate(files):
                if regex and regex.match(file_name):
                    if not files_in_progress.in_progress(file_name):
                        files_in_progress.put(file_name)
                        futures[
                            executor.submit(
                                move_file, args, file_name, period
                            )
                        ] = i
                    else:
                        if args.debug:
                            CONSOLE.print(
                                f"[bold green][Trigger][/]:  already moving {file_name}"
                            )

                else:
                    if args.debug:
                        CONSOLE.print(f"[bold green][Trigger][/]:  Ignored {file_name}")

            # Process results as they complete
            for future in as_completed(futures):
                # index = futures[future]
                try:
                    future.result()
                    files_in_progress.mark_done(files[futures[future]])
                except Exception as e:
                    index = futures[future]
                    CONSOLE.print(f"[red bold] {files[index]} had an error: {e}[/]")
                    files_in_progress.mark_done(files[index])


def move_file(
    args: argparse.Namespace, file_name: str, period:float = 0
) -> None:
    """
    Stages out a single file if it matches the regex and meets modification time criteria.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
        file_name (str): Name of the file to stage out.
    """
    threshold = period/2 # the io took half the time
    threshold = max(threshold,10)
    fast = False  # fast copy still has an error with the preload

    modification_time = time.time() - get_time(args, file_name)
    # CONSOLE.print(f"File modified {modification_time:.2} seconds ago")
    if args.ignore_mtime or modification_time >= threshold:
        CONSOLE.print(
            f"[bold green][Trigger][/][bold yellow]: Moving (copy & unlink) file {file_name} (last modified {modification_time:.3} -- threshold {threshold})[/]\n"
        )
        os.makedirs(
            os.path.dirname(file_name.replace(args.gkfs_mntdir, args.stage_out_path)),
            exist_ok=True,
        )
        if fast:
            fast_chunk_copy_file(args, file_name, threads=4)
        else:
            copy_file_and_unlink(args, file_name)
    else:
        CONSOLE.print(
            f"[bold green][Trigger][/][yellow]: {file_name} is too new (last modified {modification_time:.3})[/]\n"
        )
        files_in_progress.mark_failed(file_name)


def copy_file_and_unlink(args: argparse.Namespace, file_name: str) -> None:
    """
    Copies a file to the stage-out path and unlinks it from the source.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
        file_name (str): Name of the file to copy and unlink.
    """
    CONSOLE.print(
        f"[bold green][Trigger][/][green]: Copying {file_name} to {args.stage_out_path})[/]\n"
    )
    preloaded_call(args, f"cp {file_name} {args.stage_out_path}")

    CONSOLE.print(
        f"[bold green][Trigger][/][green]: Unlinking {file_name} to {args.stage_out_path})[/]\n"
    )
    preloaded_call(args, f" unlink {file_name}")
    CONSOLE.print(
        f"[bold green][Trigger][/][green]: Finished moving  {file_name} to {args.stage_out_path})[/]\n"
    )


def get_files(args: argparse.Namespace) -> list[str]:
    """
    Retrieves a list of files from the GekkoFS mount directory.

    Args:
        args (argparse.Namespace): Parsed command line arguments.

    Returns:
        list[str]: List of file paths.
    """
    try:
        files = preloaded_call(args, f"find {args.gkfs_mntdir}")
        if isinstance(files, str):
            files = files.strip().splitlines()
        if args.debug:
            CONSOLE.print(f"[bold green][Trigger][/][green]: Finished moving  {files}[/]\n")
        files = [f"{item}" for item in files if "." in item]
        if args.debug:
            CONSOLE.print(f"[bold green][Trigger][/][green]: Finished moving  {files}[/]\n")
        
    except Exception as e:
        if args.debug:
            CONSOLE.print(f"[bold green][Trigger][/][green]: Error encountered  {e}[/]\n")
        
        files = preloaded_call(args, f"ls -R {args.gkfs_mntdir}")
        
        if files:
            files = files.splitlines()
            # if args.debug:
            #     CONSOLE.print(f"[bold green][Trigger][/][green]: Found files are{files}[/]\n")
            files = [f for f in files if "LIBGKFS" not in f]
            files = [f"{args.gkfs_mntdir}/{item}" for item in files if "." in item]
    
    if files:
        return files
    else:
        return []


def get_time(args: argparse.Namespace, file_name: str) -> float:
    """
    Retrieves the last modification time of a file.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
        file_name (str): Name of the file.

    Returns:
        float: Last modification time of the file.
    """
    output = preloaded_call(args, f"stat --format=%Y {file_name}")
    return float(output.strip())


def preloaded_call(args: argparse.Namespace, call: str) -> str:
    """
    Executes a shell command with GekkoFS preloaded environment variables.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
        call (str): Shell command to execute.

    Returns:
        str: Output of the shell command.
    """
    call = f" LIBGKFS_HOSTS_FILE={args.host_file} LD_PRELOAD={args.ld_preload} {call}"
    return subprocess.check_output(call, shell=True, text=True)


def write_chunk(
    mmapped_file: mmap.mmap, dst: str, start: int, end: int, ld_preload: str = ""
) -> None:
    """
    Writes a chunk of the file to the destination using memory mapping.

    Args:
        mmapped_file (mmap.mmap): Memory-mapped file object.
        dst (str): Destination file path.
        start (int): Start byte of the chunk.
        end (int): End byte of the chunk.
        ld_preload (str, optional): LD_PRELOAD environment variable. Defaults to None.
    """
    # Ensure the LD_PRELOAD is set in the thread environment
    if ld_preload:
        os.environ["LD_PRELOAD"] = str(ld_preload)

    with open(dst, "r+b") as fdst:
        fdst.seek(start)
        fdst.write(mmapped_file[start:end])


def copy_metadata(src: str, dst: str, ld_preload: str = None) -> None:
    """
    Copies metadata (permissions and timestamps) from the source to the destination file.

    Args:
        src (str): Source file path.
        dst (str): Destination file path.
        ld_preload (str, optional): LD_PRELOAD environment variable. Defaults to None.
    """
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


def fast_chunk_copy_file(
    args: argparse.Namespace, file_name: str, threads: int = 4
) -> None:
    """
    Copies a single file in parallel using multiple threads.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
        file_name (str): Name of the file to copy.
        threads (int, optional): Number of threads to use. Defaults to 4.
    """
    src = file_name
    dst = f"{args.stage_out_path}/{file_name}"  # Corrected dst path
    os.environ["LIBGKFS_HOSTS_FILE"] = str(args.host_file)
    os.environ["LD_PRELOAD"] = str(args.ld_preload) if args.ld_preload else ""

    # Get file size using open() to avoid potential issues with os.path.getsize()
    with open(src, "rb") as fsrc:
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
            futures.append(
                executor.submit(
                    write_chunk, mmapped_file, dst, start, end, args.ld_preload
                )
            )

        # Wait for all threads to finish
        for future in futures:
            future.result()

    # Copy metadata using os.utime and os.chmod (these system calls will be affected by LD_PRELOAD)
    copy_metadata(src, dst, args.ld_preload)


def jit_move(settings: JitSettings) -> None:
    """
    Moves files based on JitSettings configuration.

    Args:
        settings (JitSettings): JIT settings for file staging.
    """
    # Prepare argument list based on JitSettings
    args = [
        "--stage_out_path",
        str(settings.stage_out_path),
        "--stage_in_path",
        str(settings.stage_in_path),
        "--ld_preload",
        str(settings.gkfs_intercept),
        "--host_file",
        str(settings.gkfs_hostfile),
        "--gkfs_mntdir",
        str(settings.gkfs_mntdir),
        "--ignore_mtime"
    ]
    if settings.regex_match:
        args += ["--regex", f"{str(settings.regex_match)}"]

    if settings.parallel_move:
        args += ["--parallel_move"]

    if settings.debug_lvl > 0:
        args +=  ["--debug"]
    
    # Define CLI parser
    parser = argparse.ArgumentParser(
        description="Data staging arguments", prog="file_mover"
    )

    parser.add_argument(
        "--stage_out_path",
        type=str,
        help="Cargo stage out path",
        default="/lustre/project/nhr-admire/tarraf/stage-out",
    )
    parser.add_argument(
        "--stage_in_path",
        type=str,
        help="Cargo stage in path",
        default="/lustre/project/nhr-admire/tarraf/stage-in",
    )
    parser.add_argument(
        "--regex",
        type=str,
        default=None,
        help="Files that match the regex expression are ignored during stage out",
    )
    parser.add_argument(
        "--ld_preload", type=str, default=None, help="LD_PRELOAD call to GekkoFs file."
    )
    parser.add_argument(
        "--host_file", type=str, default=None, help="Hostfile for GekkoFs."
    )
    parser.add_argument(
        "--gkfs_mntdir", type=str, default=None, help="Mount directory for GekkoFs."
    )
    parser.add_argument(
        "--ignore_mtime",action="store_true", default=True
        )
    parser.add_argument(
        "--parallel_move",action="store_true", default=False
        )
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Debug flag",
        default=False,
    )
    parser.add_argument(
        "--adaptive",
        dest="adaptive",
        help="Adaptive flag for flushing",
        default="cancel",
        choices={"skip","cancel",""}
    )

    # Parse and call mover
    parsed_args = parser.parse_args(args)

    if not settings.dry_run:
        move_files_os(parsed_args)
