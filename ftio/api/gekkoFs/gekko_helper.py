import argparse
import subprocess


def get_modification_time(args: argparse.Namespace, file_name: str) -> float:
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
