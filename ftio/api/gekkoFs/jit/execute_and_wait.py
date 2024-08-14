import subprocess
import time
import os
import threading
from rich.console import Console
from rich.panel import Panel
from rich.status import Status

from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.setup_helper import handle_sigint, jit_print, get_pid

console = Console()


def execute_block(call: str) -> subprocess.CompletedProcess[str]:
    """Executes a call and blocks till it is finished

    Args:
        call (str): bash call to execute
    """
    jit_print(f">> Executing {call}")
    out = ""
    try:
        # process = subprocess.Popen(call, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # remove capture_output=True to unbloack
        out = subprocess.run(
            call, shell=True, text=True, capture_output=True, check=True, executable="/bin/bash"
        )
    except subprocess.CalledProcessError as e:
        error_message = (
            f"[red]Command failed:[/red] {call}\n"
            f"[red]Exit code:[/red] {e.returncode}\n"
            f"[red]Output:[/red] {e.stdout.strip()}\n"
            f"[red]Error:[/red] {e.stderr.strip()}"
        )
        console.print(f"[red]{error_message}\n[/]")
        handle_sigint
        raise
    return out 


def execute_block_and_log(call: str, log_file: str) -> float:
    """Executes a call and logs it's output. This is a blocking call that
    writes the output to the log once finished.

    Args:
        call (str): bash call to execute
        log_file (str): absolute location of the log file

    Returns:
        float: execution time of the call
    """
    log_message = f">> Executing command: {call}\n"
    jit_print("[cyan]" + log_message)
    start = time.time()
    end = start
    try:
        out = subprocess.run(
            call,
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            executable="/bin/bash",
        )
        end = time.time()
        log_message += f"Output:\n{out.stdout}\n"
    except subprocess.CalledProcessError as e:
        log_message += f"Error:\n{e.stderr}\n"
        error_message = (
            f"[red]Command failed:[/red] {call}\n"
            f"[red]Exit code:[/red] {e.returncode}\n"
            f"[red]Output:[/red] {e.stdout.strip()}\n"
            f"[red]Error:[/red] {e.stderr.strip()}"
        )
        console.print(f"[red]{error_message}[/]")
        handle_sigint
        raise
    finally:
        # Write the log message to the file
        with open(log_file, "a") as file:
            file.write(log_message)
    return end - start


def execute_background(call: str, log_file: str = "", log_err_file: str = ""):
    """executes a call in the background and sets up a log dir

    Args:
        call (str): call to execute
        log_dir (str, optional): log dir directory. Defaults to "".
        error_dir (str, optional): error die directory. Defaults to "".

    Returns:
        _type_: _description_
    """
    jit_print(f"[cyan]>> Executing {call}")
    with open(log_file, "a") as file:
        file.write(f">> Executing {call}")

    if log_file and log_err_file:
        with open(log_file, "a") as log_out:
            with open(log_err_file, "w") as log_err:
                process = subprocess.Popen(
                    call, shell=True, stdout=log_out, stderr=log_err
                )
    elif log_file:
        with open(log_file, "a") as log_out:
            process = subprocess.Popen(
                call, shell=True, stdout=log_out, stderr=subprocess.STDOUT
            )
    else:
        process = subprocess.Popen(
            call, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
    return process


def execute_background_and_log(
    settings: JitSettings, call: str, log_file: str, name=""
) -> subprocess.Popen:
    """execute call in background and returns process. The output is displayed using a
    thread that reads the log file

    Args:
        settings (JitSettings): jit settings
        call (str): bash call to execute
        log_file (str): absolute location of the log file to monitor
        name (str, optional): The src of the file. If set to demon, proxy, or ftio, the output
        is colored. Defaults to "".. Defaults to "".

    Returns:
        subprocess.Popen: process
    """
    process = execute_background(call, log_file)
    get_pid(settings, name, process.pid)
    # demon is noisy
    monitor_log_file(log_file, name)
    return process


def execute_block_and_wait_line(call: str, filename: str, target_line: str) -> None:
    """executes a call and wait for a line to appear

    Args:
        call (str): bash call to execute
        filename (str): file to monitor for target_line to appear
        target_line (str): target line that need to appear in filename to
        stop the execution of this function
    """
    execute_block(call)
    wait_for_line(filename, target_line)


def execute_background_and_wait_line(call: str, filename: str, target_line: str) -> None:
    """executes a call and wait for a line to appear

    Args:
        call (str): bash call to execute
        filename (str): file to monitor for target_line to appear
        target_line (str): target line that need to appear in filename to
        stop the execution of this function
    """
    process = execute_background(call, filename)
    monitor_log_file(filename,"")
    wait_for_line(filename, target_line)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        console.print(f"[red]Error executing command:{call}")
        console.print(f"[red] Error was:\n{stderr}")
    else:
        # console.print(stdout, style="bold green")
        pass

def monitor_log_file(file: str, src: str = "") -> None:
    """monitors a file and displays its output on the console. A thread is
    in charge of monitoring the file.

    Args:
        file (str): absolute File path
        src (str, optional): The src of the file. If set to demon, proxy, or ftio, the output
        is colored. Defaults to "".
    """
    monitor_thread = threading.Thread(target=print_file, args=(file, src))
    monitor_thread.daemon = True
    monitor_thread.start()


def print_file(file, src=""):
    """Continuously monitor the log file for new lines and print them."""
    color = ""
    if src:
        if "demon" in src:
            color = "[purple4]"
        elif "proxy" in src:
            color = "[deep_pink1]"
        elif "ftio" in src:
            color = "[deep_sky_blue1]"

    with open(file, "r") as file:
        # Go to the end of the file
        file.seek(0, os.SEEK_END)
        while True:
            line = file.readline()
            if line and len(line) > 0:
                if not src or "cargo" in src:
                    print(line.rstrip())
                else:
                    console.print(
                        Panel.fit(
                            color + line.rstrip(),
                            title=src,
                            style="white",
                            border_style="white",
                            title_align="left",
                        )
                    )
            else:
                time.sleep(0.1)  # Sleep briefly to avoid high CPU usage


def wait_for_file(filename: str, timeout: int = 60) -> None:
    """Waits for a file to be created

    Args:
        file (str): absolute file path
    """
    start_time = time.time()
    with Status(
        f"[cyan]Waiting for {filename} to be created...\n", console=console
    ) as status:
        while not os.path.isfile(filename):
            passed_time = int(time.time() - start_time)
            if passed_time >= timeout:
                status.update("Timeout reached")
                console.print("[bold green]JIT [bold red]>> Timeout reached[/]")
                handle_sigint
                return

            status.update(
                f"[cyan]Waiting for {filename} to be created... ({passed_time}/{timeout}) s"
            )
            time.sleep(1)  # Wait for 1 second before checking again

        # When the file is created, update the status
        status.update(f"{filename} has been created.")
        console.print(f"[bold green]JIT [/]>>{filename} has been created.")


def wait_for_line(filename: str, target_line: str, timeout: int = 60) -> None:
    """
    Waits for a specific line to appear in a log file

    Args:
        filename (str): The path to the log file.
        target_line (str): The line of text to wait for.
    """
    start_time = time.time()

    with open(filename, "r") as file:
        # Move to the end of the file to start monitoring
        # file.seek(0, 2)  # Go to the end of the file and look at the last 10 entris
        try:
            file.seek(-2, os.SEEK_END)
        except:
            file.seek(0, 0)  # Go to the end of the file and look at the last 10 entris

        with Status(f"[cyan]Waiting for line to appear...", console=console) as status:
            while True:
                line = file.readline()
                if not line:
                    # If no line, wait and check again
                    time.sleep(0.1)
                    passed_time = int(time.time() - start_time)
                    if passed_time >= timeout:
                        status.update("Timeout reached.")
                        console.print(
                            "[bold green]JIT [bold red]>> Timeout reached. [/]"
                        )
                        handle_sigint
                        return
                    status.update(
                        f"[cyan]Waiting for line to appear... ({passed_time}/{timeout})"
                    )
                    continue

                if target_line in line:
                    status.update(f"Found target line: '{target_line}'")
                    console.print(
                        f"\n[bold green]JIT [/]>> Found target line: '{target_line}'"
                    )
                    break

