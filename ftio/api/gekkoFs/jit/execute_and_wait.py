from datetime import datetime
import multiprocessing
import subprocess
import time
import os
import re
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.markup import escape



from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.setup_helper import jit_print, get_pid

console = Console()


def execute_block(call: str, raise_exception: bool = True) -> str:
    """Executes a call and blocks till it is finished

    Args:
        call (str): bash call to execute
    """
    jit_print(f">> Executing {call}")
    out = ""
    try:
        # process = subprocess.Popen(call, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # remove capture_output=True to unblock
        out = subprocess.run(
            call,
            shell=True,
            text=True,
            capture_output=True,
            check=True,
            executable="/bin/bash",
        )
        out = out.stdout
    except subprocess.CalledProcessError as e:
        error_message = (
            f"[red]Command failed:[/red] {call}\n"
            f"[red]Exit code:[/red] {e.returncode}\n"
            f"[red]Output:[/red] {e.stdout.strip()}\n"
            f"[red]Error:[/red] {e.stderr.strip()}"
        )
        console.print(f"[red]{error_message}\n[/]")
        if raise_exception:
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
            process = subprocess.Popen(call, shell=True, stdout=log_out, stderr=log_out)
    else:
        process = subprocess.Popen(
            call, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
    return process


def execute_background_and_log(
    settings: JitSettings, call: str, log_file: str, name="", err_file: str = ""
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
    process = execute_background(call, log_file, err_file)
    get_pid(settings, name, process.pid)
    # demon is noisy
    monitor_log_file(log_file, name)
    return process



def execute_background_and_log_in_process(
    call: str, log_file: str, name="", err_file: str = ""
) :
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
    process = execute_background(call, log_file, err_file)
    # get_pid(settings, name, process.pid)
    # demon is noisy
    monitor_log_file(log_file, name)
    _, stderr = process.communicate()
    if process.returncode != 0:
        console.print(f"[red]Error executing command:{call}")
        console.print(f"[red] Error was:\n{stderr}")
    else:
        pass

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


def execute_background_and_wait_line(
    call: str, filename: str, target_line: str
) -> None:
    """executes a call and wait for a line to appear

    Args:
        call (str): bash call to execute
        filename (str): file to monitor for target_line to appear
        target_line (str): target line that need to appear in filename to
        stop the execution of this function
    """
    process = execute_background(call, filename)
    monitor_log_file(filename, "")
    wait_for_line(filename, target_line)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        console.print(f"[red]Error executing command:{call}")
        console.print(f"[red] Error was:\n{stderr}")
    else:
        # console.print(stdout, style="bold green")
        pass


def monitor_log_file(file: str, src: str = "") -> None:
    """monitors a file and displays its output on the console. A process is
    in charge of monitoring the file.

    Args:
        file (str): absolute File path
        src (str, optional): The src of the file. If set to demon, proxy, or ftio, the output
        is colored. Defaults to "".
    """
    monitor_process = multiprocessing.Process(target=print_file, args=(file, src))
    monitor_process.daemon = True
    monitor_process.start()
    


def end_of_transfer(
    settings: JitSettings, log_file: str, call: str, monitored_files: list[str] = []
) -> None:
    online = False
    stuck = False
    hits = 0
    limit = 100
    if len(monitored_files) == 0:
        monitored_files = get_files(settings, True)
        online = True
        stuck = True

    last_lines = read_last_n_lines(log_file)
    n = len(monitored_files)
    if "Transfer finished for []" in last_lines:
        # Nothing to move
        return
    elif n == 0:
        return
    else:
        with open(log_file, "r") as file:
            # Move to the end of the file
            file.seek(0, 2)
            last_pos = file.tell()
            buffer = ""

            with Status(
                f"[cyan]Waiting for end of transfer...monitoring {n} files",
                console=console,
            ) as status:
                while len(monitored_files) > 0:
                    time.sleep(0.1)  # Short sleep interval to quickly catch new lines

                    # Check if the file has grown
                    current_pos = file.tell()
                    if current_pos < last_pos:
                        # Log file was truncated or rotated, reset
                        file.seek(0, 2)
                        last_pos = file.tell()

                    # Read new content
                    file.seek(last_pos)
                    new_data = file.read()
                    last_pos = file.tell()

                    # Process the new data
                    if new_data:
                        buffer += new_data
                        lines = buffer.splitlines()

                        # Check if the last line is incomplete
                        if not new_data.endswith("\n"):
                            buffer = lines.pop()  # Save incomplete line in the buffer
                        else:
                            buffer = ""

                        # Process each line
                        for line in lines:
                            content = line.strip()
                            # jit_print(">>[cyan]**{content}")
                            if "Deleting" in content:
                                # Check if any of the monitored files are mentioned in the line
                                for name in monitored_files:
                                    if name in content:
                                        monitored_files.remove(name)
                                        jit_print(
                                            "[cyan]>> finished moving '{name}'. Remaining files ({len(monitored_files)})"
                                        )
                                        console.print(
                                            f"Waiting for {len(monitored_files)} more files to be deleted: {monitored_files}"
                                        )
                                        jit_print(
                                            "[cyan]>> Files in mount dir {monitored_files}"
                                        )
                                        status.update(
                                            f"Waiting for {len(monitored_files)} more files to be deleted: {monitored_files}"
                                        )
                                        hits = 0
                    if online:
                        # avoids dead loop for disappearing files
                        monitored_files = get_files(settings, False)
                        hits += 1
                        status.update(
                            f"Waiting for {len(monitored_files)} more files to be deleted [yellow]({hits}/{limit})[/]: {monitored_files}"
                        )
                        if hits > 4:
                            if stuck:
                                jit_print("[cyan]>> Stuck? Triggering cargo again\n")
                                _ = execute_background(
                                    call, settings.cargo_log, settings.cargo_err
                                )
                                stuck = False
                        if hits > limit:
                            jit_print("[cyan]>> Stopping stage out\n")
                            return
                # All monitored files have been processed
                timestamp = get_time()
                status.update(
                    f"\n[bold green]JIT [cyan]>> finished moving all files at  [{timestamp}]"
                )
                jit_print(
                    f"\n[cyan]>> finished moving all files at [{timestamp}]", True
                )


def get_files(settings: JitSettings, verbose=True):
    command_ls = f"LD_PRELOAD={settings.gkfs_intercept} LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} find {settings.gkfs_mntdir}"
    files = subprocess.check_output(command_ls, shell=True).decode()
    if files:
        files = files.splitlines()
        files = [f for f in files if "LIBGKFS" not in f]
        files = [file.replace(f"{settings.gkfs_mntdir}", "") for file in files if file.replace(f"{settings.gkfs_mntdir}", "")]
    
    monitored_files = files_filtered(files, settings.regex_match, verbose)
    if verbose:
        timestamp = get_time()
        jit_print(f"[cyan]>> Files that need to be stage out: [{timestamp}]")
        for f in monitored_files:
            console.print(f"[cyan]{f}[/]")

    return monitored_files


def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def files_filtered(list_of_files: list[str], regex_pattern, verbose=True) -> list[str]:
    monitored_files = []
    if list_of_files:
        if regex_pattern:
            # check if it contains file name without path (less error prone)
            while "/" in regex_pattern:
                regex_pattern = regex_pattern.split("/", 1)[1]
            if verbose:
                jit_print("[cyan]>> Cleaned Regex pattern to: {regex_pattern} ")
        regex = re.compile(regex_pattern)

        for f in list_of_files:
            if regex.match(f):
                monitored_files.append(f)

    return monitored_files


def print_file(file, src=""):
    """Continuously monitor the log file for new lines and print them."""
    color = ""
    close = ""
    wait_time = 0.05
    if src:
        if "demon" in src.lower():
            color = "[purple4]"
            wait_time = 0.1
        elif "proxy" in src.lower():
            color = "[deep_pink1]"
            wait_time = 0.1
        elif "client" in src.lower():
            color = "[gold3]"
            wait_time = 0.1
        elif "ftio" in src.lower():
            color = "[deep_sky_blue1]"
            wait_time = 0.1
        elif "error" in src.lower():
            color = "[red]"
            wait_time = 0.1

        if color:
            close = "[/]"

    with open(file, "r") as file:
        # Go to the end of the file
        file.seek(0, os.SEEK_END)
        buffer = []
        last_print_time = time.time()

        while True:
            line = file.readline()
            if line:
                buffer.append(line.rstrip())
            else:
                # If there's no new line, wait briefly
                time.sleep(wait_time)

            # Group and print the buffered lines every 0.1 seconds
            current_time = time.time()
            if current_time - last_print_time >= wait_time and buffer:
                # Print grouped lines
                content = "\n".join(buffer)
                buffer.clear()
                last_print_time = current_time

                if not src or "cargo" in src:
                    print(content)
                else:
                    console.print(
                        Panel.fit(
                            color + escape(content) + close,
                            title=src.capitalize(),
                            style="white",
                            border_style="white",
                            title_align="left",
                        )
                    )


def wait_for_file(filename: str, timeout: int = 180) -> None:
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
                jit_print("[bold red]>> Timeout reached[/]")
                return

            status.update(
                f"[cyan]Waiting for {filename} to be created... ({passed_time}/{timeout}) s"
            )
            time.sleep(1)  # Wait for 1 second before checking again

        # When the file is created, update the status
        status.update(f"{filename} has been created.")
        jit_print(f">> {filename} has been created.", True)


def wait_for_line(
    filename: str, target_line: str, msg: str = "", timeout: int = 180
) -> None:
    """
    Waits for a specific line to appear in a log file

    Args:
        filename (str): The path to the log file.
        target_line (str): The line of text to wait for.
        msg (str): Message to print
        timeout (int): maximal timeout
    """
    start_time = time.time()
    if not msg:
        msg = "Waiting for line to appear..."

    with open(filename, "r") as file:
        # Move to the end of the file to start monitoring
        # file.seek(0, 2)  # Go to the end of the file and look at the last 10 entris
        try:
            file.seek(-2, os.SEEK_END)
        except:
            file.seek(0, 0)  # Go to the end of the file and look at the last 10 entris

        with Status(f"[cyan]{msg}", console=console) as status:
            while True:
                line = file.readline()
                if not line:
                    # If no line, wait and check againet
                    time.sleep(0.01)
                    passed_time = int(time.time() - start_time)
                    if passed_time >= timeout:
                        status.update("Timeout reached.")
                        jit_print("[bold red]>> Timeout reached[/]", True)
                        return
                    status.update(f"[cyan]{msg} ({passed_time}/{timeout})")
                    continue

                if target_line in line:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    status.update(f"Found target line: '{target_line}'")
                    jit_print(f"[cyan]>> Stopped waiting at [{timestamp}]", True)
                    break


def read_last_n_lines(filename, n=3):
    """Read the last `n` lines of a file."""
    with open(filename, "rb") as f:
        # Move the pointer to the end of the file
        f.seek(0, 2)
        file_size = f.tell()

        # Initialize variables
        lines = []
        buffer = b""
        pointer = file_size

        while pointer > 0 and len(lines) < n:
            # Move the pointer backwards by one byte and read
            pointer -= 1
            f.seek(pointer)
            buffer = f.read(1) + buffer

            # If a newline is found, add the line to the list
            if buffer.startswith(b"\n") or pointer == 0:
                lines.append(buffer.decode("utf-8"))
                buffer = b""

        return lines[-n:]
