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

import argparse
import math
import mmap
import os
import re
import time
from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)

from ftio.api.gekkoFs.file_queue import FileQueue
from ftio.api.gekkoFs.gekko_helper import preloaded_call, get_modification_time
from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()
CONSOLE.set(True)

files_in_progress = FileQueue()


def move_files_os(
    args: argparse.Namespace, parallel: bool = False, period: float = 0
) -> None:
    """
    Moves files and directories from the source directory to the stage-out path.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
        parallel (bool, optional): Whether to use parallel processing for file moving.
            modification time checks. Defaults to False.
        period (float, optional): Time period for file modification checks. Defaults to 0.
    """
    CONSOLE.print("[bold green][Trigger][/] Moving files\n")
    args.ld_preload = args.ld_preload.replace("libc_", "")
    if not os.path.exists(args.stage_out_path):
        os.makedirs(args.stage_out_path)

    # Iterate over all items in the source directory
    files = get_files(args)
    if args.parallel_move:
        parallel = True
        text = (
            f"[bold green][Trigger][/] {len(files)} files flagged to move in parallel\n"
        )
    else:
        text = f"[bold green][Trigger][/] {len(files)} files flagged to move\n"
    CONSOLE.print(text)

    if args.debug:
        CONSOLE.print(f"[bold green][Trigger][/] Files are:\n {files}\n")

    # Ensure the target directory exists
    os.makedirs(args.stage_out_path, exist_ok=True)
    # Check if to submit files or folders
    # items_to_submit = get_items_to_submit(files, args, "files")
    items_to_submit = get_items_to_submit(files, args, "folder")

    # Step 3: Submit tasks to the executor ((only move the files if they are not
    # already in progress
    futures: dict = {}
    num_workers = 1 if not parallel else 10

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for idx, item in enumerate(items_to_submit):
            # check that the item is not in progress and not  not in the ignored list
            if not files_in_progress.in_progress(
                item
            ) and not files_in_progress.is_ignored(args, item):
                files_in_progress.put(item)
                futures[executor.submit(move_item, args, item, period)] = idx
                if args.debug:
                    CONSOLE.print(f"[bold green][Trigger][/]: moving {item}")
            else:
                if args.debug:
                    CONSOLE.print(f"[bold yellow][Trigger][/]: already moving {item}")

        CONSOLE.print(
            f"[bold green][Trigger][/]: Finished submitting {len(futures)} futures. "
            f"Using {num_workers} workers for processing"
        )
        if args.debug:
            CONSOLE.print(
                f"[bold green][Trigger][/]: files in process are: {files_in_progress}"
            )

        for future in as_completed(futures):
            try:
                future.result()
                files_in_progress.mark_done(items_to_submit[futures[future]])
            except Exception as e:
                index = futures[future]
                CONSOLE.print(f"[red bold] {items_to_submit[index]} had an error: {e}[/]")
                files_in_progress.mark_done(items_to_submit[index])


def get_items_to_submit(files: list, args: argparse.Namespace, mode: str = "files"):
    """
    Determine which items (files or folders) should be submitted based on
    regex filtering and the submission mode.

    If `mode` includes "folder", files are grouped by their parent directory.
    Matching files (according to `args.regex`) are checked against all files
    in the folder:
      - If all files in a folder match, the entire folder is submitted.
      - Otherwise, only the matching files from that folder are submitted.

    If `mode` does not include "folder", all provided files are returned.

    Args:
        files (list[str]): List of file paths to consider for submission.
        args (Namespace): Parsed arguments containing at least:
            - regex (str | None): Regex pattern to filter files.
            - debug (bool): Whether to print debug information.
        mode (str, optional): Submission mode. If it contains "folder", directory-level
            grouping and filtering logic is applied.

    Returns:
        list[str]: List of items (file paths or folder paths) to be submitted.
    """
    regex = None
    # Compile the regex pattern if provided
    if args.regex:
        CONSOLE.print(f"[bold green][Trigger][/] Using pattern: {args.regex}\n")
        regex = re.compile(args.regex)

    if "folder" in mode:
        # check if we can move the entire folder:
        #  Step 0: Group all files by their parent folder
        folder_to_all_files: dict[str, list[str]] = {}
        for file_path in files:
            folder = file_path.rsplit("/", 1)[0] if "/" in file_path else "."
            # CONSOLE.print(f" Processing file: {file_path} -> folder: {folder}")
            folder_to_all_files.setdefault(folder, []).append(file_path)

        # CONSOLE.print(f"Final folder mapping: {folder_to_all_files}")
        CONSOLE.print(f"[bold green][Trigger][/] Using regex: {regex}")

        # Step 1: Filter files by regex (only candidates to move)
        matching_files: list[str] = [f for f in files if regex and regex.match(f)]

        # Step 2: Decide whether to submit folder or individual files
        items_to_submit: list[str] = []

        for folder, all_files_in_folder in folder_to_all_files.items():
            matching_files_in_folder = [
                f for f in all_files_in_folder if f in matching_files
            ]
            # If all files in the folder match, submit the folder
            if matching_files_in_folder:
                if set(all_files_in_folder) == set(matching_files_in_folder):
                    items_to_submit.append(folder)
                    if args.debug:
                        CONSOLE.print(
                            f"[bold green][Trigger][/] Will move folder: {folder}\n"
                        )
                else:
                    items_to_submit.extend(matching_files_in_folder)
                    if args.debug:
                        CONSOLE.print(
                            f"[bold green][Trigger][/] Will move "
                            f"{len(matching_files_in_folder)} from {folder}\n"
                        )
    else:
        items_to_submit = files

    return items_to_submit


def move_item(args: argparse.Namespace, item: str, period: float = 0) -> None:
    """
    Stages out a single file if it matches the regex and meets modification time criteria.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
        item (str): Name of the file to stage out.
    """
    fast = False  # fast copy still has an error with the preload

    # threshold = period / 2  # the IO took half the time
    threshold = 0  # already considered in calculation of flush time
    threshold = max(threshold, 5)

    item_time = get_modification_time(args, item)
    modification_time = time.time() - item_time
    # CONSOLE.print(f"File modified {modification_time:.2} seconds ago")
    if args.ignore_mtime or modification_time >= threshold:
        CONSOLE.print(
            f"[bold green][Trigger][/][bold yellow]: Moving (copy & unlink) item {item} (last modified {modification_time:.3} > threshold {threshold})[/]\n"
        )
        os.makedirs(
            os.path.dirname(item.replace(args.gkfs_mntdir, args.stage_out_path)),
            exist_ok=True,
        )
        if fast:
            # Todo: add mode for folder. However this currenlty not used
            fast_chunk_copy_file(args, item, threads=4)
        else:
            copy_file_and_unlink(args, item)

        CONSOLE.print(
            f"[bold green][Trigger][/][yellow]: {len(files_in_progress)} files still in the queue."
        )
    else:
        CONSOLE.print(
            f"[bold green][Trigger][/][yellow]: Skipping item {item} is too new (last modified {modification_time:.3} < threshold {threshold})[/]\n"
        )
        files_in_progress.mark_failed(item)


def copy_file_and_unlink(args: argparse.Namespace, item: str) -> None:
    """
    Copies a file or folder to the stage-out path and removes it from the source.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
        item (str): Name of the file or folder to copy and remove.
    """
    if "." in item.split("/")[-1]:  # file
        cp_cmd = f"cp {item} {args.stage_out_path}"
        remove_cmd = f"unlink {item}"
    else:  # folder
        cp_cmd = f"cp -r {item} {args.stage_out_path}"
        # remove_cmd = f"rm -rf {item}"
        remove_cmd = f"find {item} -type f -exec unlink {{}} \\;"

    CONSOLE.print(f"[bold green][Trigger][/] Copying {item} to {args.stage_out_path})\n")
    start = time.time()
    preloaded_call(args, cp_cmd)
    copy_time = time.time() - start
    CONSOLE.print(
        f"[bold green][Trigger][/] Finished moving {item} to {args.stage_out_path})\n"
    )

    start = time.time()
    CONSOLE.print(f"[bold green][Trigger][/] Removing {item} from source\n")
    try:
        preloaded_call(args, remove_cmd)
    except Exception as e:
        CONSOLE.print(
            f"[bold red][Trigger][/]Exception encounter during {remove_cmd}: {e}"
        )
        if "-r" in remove_cmd:
            try:
                remove_cmd = f"find {item} -type f -exec unlink {{}} \\;"
                preloaded_call(args, remove_cmd)
            except Exception as e:
                CONSOLE.print(
                    f"[bold red][Trigger][/]Exception encounter during {remove_cmd}: {e}"
                )
        files_in_progress.put_ignore(args, item)
        CONSOLE.print(f"[bold yellow][Trigger][/]Added {item} to ignore queue ")

    CONSOLE.print(
        f"[bold green][Trigger][/][green]: Times  for {item}: copied in {copy_time} s, "
        f"deleted in {time.time()-start} s[/]\n"
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
            CONSOLE.print(
                f"[bold green][Trigger][/][green]: Finished moving  {files}[/]\n"
            )
        files = [f"{item}" for item in files if "." in item]
        if args.debug:
            CONSOLE.print(
                f"[bold green][Trigger][/][green]: Finished moving  {files}[/]\n"
            )

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


def write_chunk(
    mmapped_file: mmap.mmap,
    dst: str,
    start: int,
    end: int,
    ld_preload: str = "",
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
        "--ignore_mtime",
    ]
    if settings.regex_match:
        args += ["--regex", f"{str(settings.regex_match)}"]

    if settings.parallel_move:
        args += ["--parallel_move"]

    if settings.debug_lvl > 0:
        args += ["--debug"]

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
    parser.add_argument("--ignore_mtime", action="store_true", default=True)
    parser.add_argument("--parallel_move", action="store_true", default=False)
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
        choices={"skip", "cancel", ""},
    )

    # Parse and call mover
    parsed_args = parser.parse_args(args)

    if not settings.dry_run:
        move_files_os(parsed_args)
