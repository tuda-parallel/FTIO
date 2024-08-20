import sys
import subprocess
import getopt
import os
import signal
import time
from rich.console import Console
from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.jittime import JitTime

console = Console()


def is_port_in_use(port_number):
    try:
        # Run the netstat command and search for the port number
        netstat_output = subprocess.check_output(
            f"netstat -tlpn | grep ':{port_number} '",
            shell=True,
            stderr=subprocess.STDOUT,
        ).decode("utf-8")
        # If output is found, the port is in use
        if netstat_output:
            console.print(
                f"[bold red]Error: Port {port_number} is already in use...[/bold red]"
            )
            return True  # Port is in use
    except subprocess.CalledProcessError:
        # grep returns a non-zero exit status if it finds no matches
        console.print(f"[bold blue]Port {port_number} is available.[/bold blue]")
        return False  # Port is free


def check_port(settings: JitSettings):
    """Check if a port is available and terminate any existing process using it."""
    if is_port_in_use(settings.port):
        jit_print(
            f"[bold red]Error: Port {settings.port} is already in use on {settings.address_ftio}. Terminating existing process...[/]"
        )

        # Identify the process ID using the settings.port
        try:
            process_output = (
                subprocess.check_output(
                    f"netstat -nlp | grep :{settings.port} ", shell=True
                )
                .decode()
                .strip()
            )
            process_id = process_output.split()[6].split("/")[0]

            if process_id:
                jit_print(f"[bold yellow]Terminating process with PID: {process_id}[/]")
                os.kill(int(process_id), 9)
                jit_print(
                    f"[bold green]Using port {settings.port} on {settings.address_ftio}.[/]"
                )
                return 0
            else:
                jit_print(
                    f"[bold red]Failed to identify process ID for PORT {settings.port}.[/]"
                )
                exit(1)
        except subprocess.CalledProcessError as e:
            jit_print(f"[bold red]Failed to retrieve process information: {e}[/]")
            exit(1)
    else:
        jit_print(
            f"[bold green]Using port {settings.port} on {settings.address_ftio}.[/]"
        )


def parse_options(settings: JitSettings, args: list) -> None:

    try:
        opts, args = getopt.getopt(
            args,
            "a:p:n:c:r:t:j:l:i:e:xh",
            [
                "address=",
                "port=",
                "nodes=",
                "procs=",
                "procs_list=",
                "max-time=",
                "job-id=",
                "log-name=",
                "install-location=",
                "exclude=",
                "exclude-all",
                "help",
            ],
        )
    except getopt.GetoptError as err:
        console.print(f"[bold red]Error: {err}[/bold red]")
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-a", "--address"):
            settings.address_ftio = arg
        elif opt in ("-p", "--port"):
            settings.port = arg
        elif opt in ("-n", "--nodes"):
            settings.nodes = int(arg)
        elif opt in ("-t", "--max-time"):
            settings.max_time = int(arg)
        elif opt in ("-j", "--job-id"):
            settings.job_id = int(arg)
        elif opt in ("-l", "--log-name"):
            settings.log_dir = arg
        elif opt in ("-i", "--install-location"):
            settings.install_location = arg
            install_all(settings)
        elif opt in ("-p","--procs"):
            settings.procs = int(arg)
        elif opt in("-r", "--procs_list"):
            # Split the argument by comma to get the list of numbers
            procs_list = arg.split(",")

            # Convert the list of strings to a list of integers
            try:
                procs_list = [int(proc) for proc in procs_list]
            except ValueError:
                console.print("[bold red]Invalid --procs value. It must be a comma-separated list of numbers.[/]")
                sys.exit(1)

            # Check the number of elements and assign accordingly
            if len(procs_list) > 5:
                console.print("[bold red]Too many values for --procs. Maximum is 5.[/]")
                sys.exit(1)
            elif len(procs_list) > 0:
                settings.procs_app = int(procs_list[0])
            if len(procs_list) > 1:
                settings.procs_demon = int(procs_list[1])
            if len(procs_list) > 2:
                settings.procs_proxy = int(procs_list[2])
            if len(procs_list) > 3:
                settings.procs_cargo = int(procs_list[3])
            if len(procs_list) > 4:
                settings.procs_ftio = int(procs_list[4])
        elif opt in ("-e", "--exclude"):
            jit_print("[bold yellow]>> Excluding: [/]")
            if not arg or arg.startswith("-"):
                settings.exclude_ftio = True
                console.print("[yellow]- ftio[/]")
            else:
                excludes = arg.split(",")
                for exclude in excludes:
                    if exclude == "ftio":
                        settings.exclude_ftio = True
                        console.print("[yellow]- ftio[/]")
                    elif exclude == "cargo":
                        settings.exclude_cargo = True
                        console.print("[yellow]- cargo[/]")
                    elif exclude in ("gkfs", "demon", "proxy"):
                        if exclude == "gkfs":
                            settings.exclude_demon = True
                            settings.exclude_proxy = True
                            console.print("[yellow]- gkfs[/]")
                        elif exclude == "demon":
                            settings.exclude_demon = True
                            console.print("[yellow]- demon[/]")
                        elif exclude == "proxy":
                            settings.exclude_proxy = True
                            console.print("[yellow]- proxy[/]")
                    elif exclude == "all":
                        settings.exclude_all = True
                        console.print("[yellow]- all[/]")
                    else:
                        console.print(
                            f"[bold green]JIT >>[bold red] Invalid exclude option: {exclude} [/]"
                        )
                        sys.exit(1)
        elif opt in ("-x", "--exclude-all"):
            settings.exclude_all = True
        elif opt in ("-h", "--help"):
            error_usage(settings)
            sys.exit(1)
        

        else:
            console.print(f"[bold red]Invalid option: {opt}[/]")
            error_usage(settings)
            sys.exit(1)

    settings.update()


def error_usage(settings: JitSettings):
    console.print(
        f"""
[bold]Usage: {sys.argv[0]} [OPTION] ... [/]
    -a | --address: X.X.X.X <string>
        default: [bold yellow]{settings.address_ftio}[/]
        Address where FTIO is executed. On a cluster, this is found 
        automatically by determining the address of node where FTIO 
        runs.

    -p | --port: XXXX <int>
        default: [bold yellow]{settings.port}[/]
        port for FTIO and GekkoFS.

    -n | --nodes: X <int>
        default: [bold yellow]{settings.nodes}[/]
        number of nodes to run the setup. In cluster mode, FTIO is 
        executed on a single node, while the rest (including the
        application) get X-1 nodes.

    -c | --procs: X <int>
        default: [bold yellow]{settings.procs}[/]
        if procs_list is skipped, this is the default number of procs assigned to all
        
    -r | --procs_list: x,x,..,x <list>
        default: [bold yellow]{settings.procs_app},{settings.procs_demon},{settings.procs_proxy},{settings.procs_cargo},{settings.procs_ftio}[/]
        List of procs per node for app, demon, proxy, cargo, and ftio, respectively.
        Assignment is from right to left depending on the length of the list

    -t | --max-time: X <int>
        default: [bold yellow]{settings.max_time}[/]
        max time for the execution of the setup in minutes.

    -j | --job-id: X <int>
        default: [bold yellow] Auto detected[/]
        Skips allocating new resources and uses job id.
    
    -l | --log-name: <str>
        default: Auto set to number of nodes and job ID
        if provided, sets the name of the directory where the logs are stored.

    -e | --exclude: <str>,<str>,...,<str>
        default: ftio
        If this flag is provided, the setup is executed without the tool(s).
        Supported options include: ftio, demon, proxy, gkfs (demon + proxy), 
        cargo, and all (same as -x).

    -x | --exclude-all <list>
        default: [bold yellow]{settings.exclude_all}[/]
        If this flag is provided, the setup is executed without FTIO, 
        GekkoFs, and Cargo.

    -i | --install-location: full_path <str>
        default: [bold yellow]{settings.install_location}[/]
        Installs everything in the provided directory.

---- exit ----
    """
    )


def abort():
    console.print("[bold green]JIT [bold red] >>> Aborting installation[/]")
    exit(1)


def install_all(settings: JitSettings) -> None:
    with console.status("[bold green]Starting installation...") as status:
        try:
            # Create directory
            console.print("[bold green]JIT >>> Creating directory[/]")
            status.update("[bold green]JIT >>> Creating directory[/]",speed=30)
            os.makedirs(settings.install_location, exist_ok=True)

            # Clone GKFS
            console.print("[bold green]JIT >>> Installing GKFS[/]")
            status.update("[bold green]JIT >>> Installing GKFS[/]",speed=30)
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--recurse-submodules",
                    "https://storage.bsc.es/gitlab/hpc/gekkofs.git",
                ],
                cwd=settings.install_location,
                check=True,
            )
            os.chdir(os.path.join(settings.install_location, "gekkofs"))
            subprocess.run(["git", "pull", "--recurse-submodules"], check=True)
            os.chdir(settings.install_location)

            # Build GKFS
            console.print("[bold green]JIT >>> Building GKFS[/]")
            status.update("[bold green]JIT >>> Building GKFS[/]",speed=30)
            subprocess.run(
                [
                    "gekkofs/scripts/gkfs_dep.sh",
                    "-p",
                    "default_zmq",
                    f"{settings.install_location}/iodeps/git",
                    f"{settings.install_location}/iodeps",
                ],
                check=True,
            )
            build_dir = os.path.join(settings.install_location, "gekkofs", "build")
            os.makedirs(build_dir, exist_ok=True)
            subprocess.run(
                [
                    "cmake",
                    "-DCMAKE_BUILD_TYPE=Release",
                    f"-DCMAKE_PREFIX_PATH={settings.install_location}/iodeps",
                    "-DGKFS_BUILD_TESTS=OFF",
                    f"-DCMAKE_INSTALL_PREFIX={settings.install_location}/iodeps",
                    "-DGKFS_ENABLE_CLIENT_METRICS=ON",
                    "..",
                ],
                cwd=build_dir,
                check=True,
            )
            subprocess.run(["make", "-j", "4", "install"], cwd=build_dir, check=True)

            console.print("[bold green]JIT >>> GEKKO installed[/]")
            status.update("[bold green]JIT >>> GEKKO installed[/]",speed=30)

            console.print("[bold green]JIT >>> Installing Cereal[/]")
            status.update("[bold green]JIT >>> Installing Cereal[/]",speed=30)
            subprocess.run(
                ["git", "clone", "https://github.com/USCiLab/cereal"],
                cwd=settings.install_location,
                check=True,
            )
            os.chdir(os.path.join(settings.install_location, "cereal"))
            build_dir = os.path.join(settings.install_location, "cereal", "build")
            os.makedirs(build_dir, exist_ok=True)
            subprocess.run(
                [
                    "cmake",
                    f"-DCMAKE_PREFIX_PATH={settings.install_location}/iodeps",
                    f"-DCMAKE_INSTALL_PREFIX={settings.install_location}/iodeps",
                    "..",
                ],
                cwd=build_dir,
                check=True,
            )
            subprocess.run(["make", "-j", "4", "install"], cwd=build_dir, check=True)

            # Install Cargo Dependencies: Thallium
            console.print("[bold green]JIT >>> Installing Thallium[/]")
            status.update("[bold green]JIT >>> Installing Thallium[/]",speed=30)
            subprocess.run(
                ["git", "clone", "https://github.com/mochi-hpc/mochi-thallium"],
                cwd=settings.install_location,
                check=True,
            )
            os.chdir(os.path.join(settings.install_location, "mochi-thallium"))
            build_dir = os.path.join(
                settings.install_location, "mochi-thallium", "build"
            )
            os.makedirs(build_dir, exist_ok=True)
            subprocess.run(
                [
                    "cmake",
                    f"-DCMAKE_PREFIX_PATH={settings.install_location}/iodeps",
                    f"-DCMAKE_INSTALL_PREFIX={settings.install_location}/iodeps",
                    "..",
                ],
                cwd=build_dir,
                check=True,
            )
            subprocess.run(["make", "-j", "4", "install"], cwd=build_dir, check=True)

            # Clone and Build Cargo
            console.print("[bold green]JIT >>> Installing Cargo[/]")
            status.update("[bold green]JIT >>> Installing Cargo[/]",speed=30)
            subprocess.run(
                ["git", "clone", "https://storage.bsc.es/gitlab/hpc/cargo.git"],
                cwd=settings.install_location,
                check=True,
            )
            os.chdir(os.path.join(settings.install_location, "cargo"))
            replace_line_in_file(
                "src/master.cpp", 332, f'  auto patternFile = "{settings.regex_file}";'
            )

            build_dir = os.path.join(settings.install_location, "cargo", "build")
            os.makedirs(build_dir, exist_ok=True)
            subprocess.run(
                [
                    "cmake",
                    "-DCMAKE_BUILD_TYPE=Release",
                    f"-DCMAKE_PREFIX_PATH={settings.install_location}/iodeps",
                    f"-DCMAKE_INSTALL_PREFIX={settings.install_location}/iodeps",
                    "..",
                ],
                cwd=build_dir,
                check=True,
            )
            subprocess.run(["make", "-j", "4", "install"], cwd=build_dir, check=True)

            console.print("[bold green]JIT >>> Cargo installed[/]")
            status.update("[bold green]JIT >>> Cargo installed[/]",speed=30)

            # Build IOR
            console.print("[bold green]JIT >>> Installing IOR[/]")
            status.update("[bold green]JIT >>> Installing IOR[/]",speed=30)
            subprocess.run(
                ["git", "clone", "https://github.com/hpc/ior.git"],
                cwd=settings.install_location,
                check=True,
            )
            os.chdir(os.path.join(settings.install_location, "ior"))
            subprocess.run(["./bootstrap"], check=True)
            subprocess.run(["./configure"], check=True)
            subprocess.run(["make", "-j", "4"], check=True)

            console.print("[bold green]JIT >> Installation finished[/]")
            status.update("[bold green]JIT >> Installation finished[/]",speed=30)
            console.print("\n>> Ready to go <<")
            status.update("\n>> Ready to go <<",speed=30)
            console.print("Call: ./jit.sh -n NODES -t MAX_TIME")
            status.update("Call: ./jit.sh -n NODES -t MAX_TIME",speed=30)

        except subprocess.CalledProcessError as e:
            console.print("[bold green]JIT [bold red] >>> Error encountered: {e}[/]")
            status.update("[bold green]JIT [bold red] >>> Error encountered: {e}[/]",speed=30)
            abort()


def replace_line_in_file(file_path, line_number, new_line_content):
    try:
        # Read the existing file content
        with open(file_path, "r") as file:
            lines = file.readlines()

        # Replace the specific line (line_number - 1 because list indices start at 0)
        if line_number - 1 < len(lines):
            lines[line_number - 1] = new_line_content + "\n"
        else:
            raise IndexError(
                "Line number exceeds the total number of lines in the file."
            )

        # Write the modified content back to the file
        with open(file_path, "w") as file:
            file.writelines(lines)

        print(f"Successfully replaced line {line_number} in {file_path}.")

    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
    except IndexError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def cancel_jit_jobs(settings:JitSettings):
    if settings.job_id == 0:
        # Check if the hostname contains 'cpu' or 'mogon'
        hostname = subprocess.check_output("hostname", shell=True).decode().strip()
        if "cpu" in hostname or "mogon" in hostname:
            # Get the list of job IDs with the name "JIT"
            try:
                jit_jobs = (
                    subprocess.check_output(
                        "squeue --me --name=JIT --format=%A", shell=True
                    )
                    .decode()
                    .strip()
                    .split("\n")[1:]
                )
            except subprocess.CalledProcessError:
                jit_jobs = []

            if not jit_jobs:
                return

            # Print the list of JIT jobs
            job_list = "\n".join(jit_jobs)
            console.print(
                "[bold green]JIT [bold yellow]>> The following jobs with the name 'JIT' were found:[/]"
            )
            console.print(job_list)

            # Prompt the user to confirm cancellation
            confirmation = (
                input("Do you want to cancel all 'JIT' jobs? (yes/no): ").strip().lower()
            )

            if confirmation in {"yes", "y", "ye"}:
                for job_id in jit_jobs:
                    subprocess.run(f"scancel {job_id}", shell=True, check=True)
                    console.print(
                        f"[bold green]JIT [bold cyan]>> Cancelled job ID {job_id}[/]"
                    )
                console.print(
                    "[bold green]JIT [bold green]>> All 'JIT' jobs have been cancelled.[/]"
                )
            else:
                console.print("[bold green]JIT [bold yellow]>> No jobs were cancelled.[/]")




def relevant_files(settings: JitSettings, verbose: bool = False):

    if verbose:  # Mimicking checking for the number of arguments
        console.print(f"[bold green]JIT [/][cyan]>> Setting up ignored files[/]")

    # Create or update the regex file with the settings.regex_match
    with open(settings.regex_file, "w") as file:
        file.write(f"{settings.regex_match}\n")

    if verbose:
        console.print(
            f"[bold green]JIT [/][cyan]>> Files that match {settings.regex_match} are ignored [/]"
        )

    # Display the contents of the regex file
    with open(settings.regex_file, "r") as file:
        content = file.read()
    if settings.debug:
        console.print(
            f"[bold green]JIT [cyan]>> content of {settings.regex_file}: \n{content}[/]"
        )


def reset_relevant_files(settings: JitSettings) -> None:
    if settings.cluster:
        console.print(f"[bold green] JIT [/][cyan]>> Resetting ignored files[/]")
        # Write the default regex pattern to the file
        settings.regex_match=".*"
        with open(settings.regex_file, "w") as file:
            
            file.write(f"{settings.regex_match}\n")
        # Optionally console.print the contents of the regex file
        # with open(settings.regex_file, 'r') as file:
        #     content = file.read()
        # console.print(f"[bold green] JIT [bold cyan]>> cat {settings.regex_file}: \n{content} [/]\n")


def total_time(log_dir):
    time_log_file = os.path.join(log_dir, "time.log")

    # Calculate total time from the log file
    try:
        with open(time_log_file, "r") as file:
            lines = file.readlines()
        total_time = sum(float(line.split()[1]) for line in lines if "seconds" in line)
    except FileNotFoundError:
        total_time = 0

    # Print and append total time to the log file
    result = f"\n JIT --> Total Time: {total_time}\n"
    console.print("[bold green]" + result + "[/]")
    with open(time_log_file, "a") as file:
        file.write(result)


def allocate(settings: JitSettings) -> None:
    settings.app_nodes = 1
    if settings.cluster:

        #allocate if needed 
        if settings.job_id == 0:
            # Allocating resources
            console.print("[bold green]JIT [green] ####### Allocating resources[/]")

            call = f"salloc -N {settings.nodes} -t {settings.max_time} {settings.alloc_call_flags}"
            console.print(f"[bold green]JIT [cyan] >> Executing: {call} [/]")

            # Execute the salloc command
            subprocess.run(call, shell=True, check=True)

            # Get JIT_ID
            try:
                result = subprocess.run(
                    "squeue -o '%.18i %.9P %.8j %.8u %.2t %.10M %.6D %R' | grep ' JIT ' | sort -k1,1rn | head -n 1 | awk '{print $1}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                settings.job_id = int(result.stdout.strip())
            except subprocess.CalledProcessError:
                settings.job_id = 0
        else:
            console.print(f"[bold green]JIT [green] ####### Using allocation with id: {settings.job_id}[/]")

        # Get NODES_ARR
        if settings.job_id:
            try:
                nodes_result = subprocess.run(
                    f"scontrol show hostname $(squeue -j {settings.job_id} -o '%N' | tail -n +2)",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                nodes_arr = nodes_result.stdout.splitlines()
                if nodes_arr:
                    try:
                        nodes_arr = nodes_arr[:settings.nodes]
                    except IndexError:
                        pass 
                    console.print(f"[bold green]JIT [red] >> Unable to decrease number of nodes. Using {settings.nodes}[/]")
            except subprocess.CalledProcessError:
                nodes_arr = []

            # Write to hostfile_mpi
            with open(os.path.expanduser("~/hostfile_mpi"), "w") as file:
                file.write("\n".join(nodes_arr) + "\n")

            if nodes_arr:
                # Get FTIO node
                settings.ftio_node = nodes_arr[-1]
                # Get node for single commands
                settings.single_node = nodes_arr[0]

                if len(nodes_arr) > 1:
                    settings.ftio_node_command = f"--nodelist={settings.ftio_node}"
                    settings.app_nodes_command = f"--nodelist={','.join(n for n in nodes_arr if n != settings.ftio_node)}"
                    settings.single_node_command = f"--nodelist={settings.single_node}"
                    settings.app_nodes = len(nodes_arr) - 1

                    # Remove FTIO node from hostfile_mpi
                    with open(os.path.expanduser("~/hostfile_mpi"), "r") as file:
                        lines = file.readlines()
                    with open(os.path.expanduser("~/hostfile_mpi"), "w") as file:
                        file.writelines(
                            line for line in lines if line.strip() != settings.ftio_node
                        )

                console.print(
                    f"[bold green]JIT [green] >> JIT Job Id: {settings.job_id} [/]"
                )
                console.print(
                    f"[bold green]JIT [green] >> Allocated Nodes: {len(nodes_arr)} [/]"
                )
                console.print(
                    f"[bold green]JIT [green] >> FTIO Node: {settings.ftio_node} [/]"
                )
                console.print(
                    f"[bold green]JIT [green] >> APP Node command: {settings.app_nodes_command} [/]"
                )
                console.print(
                    f"[bold green]JIT [green] >> FTIO Node command: {settings.ftio_node_command} [/]"
                )

                # Print contents of hostfile_mpi
                with open(os.path.expanduser("~/hostfile_mpi"), "r") as file:
                    hostfile_content = file.read()
                console.print(
                    f"[bold green]JIT [cyan] >> content of ~/hostfile_mpi: \n{hostfile_content} [/]"
                )
        else:
            console.print(
                "[bold gree]JIT [bold red]>> JIT_ID could not be retrieved[/]"
            )






def get_pid(settings: JitSettings, name: str, pid: int):
    if settings.cluster:
        call = f"ps aux | grep 'srun' | grep '{settings.job_id}' | grep '{name}' | grep -v grep | tail -1 | awk '{{print $2}}'"
        res = subprocess.run(call, shell=True, check=True, capture_output=True, text=True)
        if res.stdout.strip():
            pid = res.stdout.strip() 

    if name.lower() in "cargo":
        settings.cargo_pid = pid
        console.print(f"[green ]JIT >> Cargo startup successful. PID is {pid}[/]")
    elif name.lower() in "gkfs_demon":
        settings.gekko_demon_pid = pid
        console.print(f"[green ]JIT >> Gekko demon startup successful. PID is {pid}[/]")
    elif name.lower() in "gkfs_proxy":
        settings.gekko_proxy_pid = pid
        console.print(f"[green ]JIT >> Gekko proxy startup successful. PID is {pid}[/]")
    elif name.lower() in "ftio" or name.lower() in "predictor_jit":
        settings.ftio_pid = pid
        console.print(f"[green ]JIT >> Ftio startup successful. PID is {pid}[/]")


# Function to handle SIGINT (Ctrl+C)
def handle_sigint(settings: JitSettings):
    console.print("[bold green]JIT > Keyboard interrupt detected. Exiting script.[/]")
    soft_kill(settings)
    hard_kill(settings)
    if settings.cluster:
        _ = subprocess.run(f"scancel {settings.job_id}", shell=True, text=True, capture_output=True, check=True, executable="/bin/bash"
        )
    sys.exit(0)


def soft_kill(settings: JitSettings) -> None:
    console.print("\n[bold green]JIT[bold green] ####### Soft kill [/]")

    if settings.exclude_ftio == False:
        try:
            shut_down(settings, "FTIO", settings.ftio_pid)
            console.print("[bold green]JIT[bold cyan] >> killed FTIO [/]")
        except:
            console.print("[bold green]JIT[bold cyan] >> Unable to soft kill FTIO [/]")

    if settings.exclude_demon == False:
        try:
            shut_down(settings, "GEKKO", settings.gekko_demon_pid)
            console.print("[bold green]JIT[bold cyan] >> killed GEKKO DEMON [/]")
        except:
            console.print("[bold green]JIT[bold cyan] >> Unable to soft kill GEKKO DEMON [/]")

    if settings.exclude_proxy == False:
        try:
            shut_down(settings, "GEKKO", settings.gekko_proxy_pid)
            console.print("[bold green]JIT[bold cyan] >> killed GEKKO PROXY [/]")
        except:
            console.print("[bold green]JIT[bold cyan] >> Unable to soft  kill GEKKO PROXY [/]")

    if settings.exclude_cargo == False:
        try:
            shut_down(settings, "CARGO", settings.cargo_pid)
            console.print("[bold green]JIT[bold cyan] >> killed CARGO [/]")
        except:
            console.print("[bold green]JIT[bold cyan] >> Unable to soft kill CARGO [/]")


def hard_kill(settings) -> None:
    console.print(f"\n[bold green]####### Hard kill[/]")

    if settings.cluster:
        # Cluster environment: use `scancel` to cancel the job
        _ = subprocess.run(
            f"scancel {settings.job_id}", shell=True, text=True, capture_output=True, check=True, executable="/bin/bash"
        )
    else:
        # Non-cluster environment: use `kill` to terminate processes
        processes = [
            settings.gkfs_demon,
            settings.gkfs_proxy,
            settings.cargo,
            f"{os.path.dirname(settings.ftio_activate)}/predictor_jit",
        ]

        for process in processes:
            try:
                # Find process IDs and kill them
                kill_command = f"ps -aux | grep {process} | grep -v grep | awk '{{print $2}}' | xargs kill"
                while(kill_command):
                    _ = subprocess.run(
                        kill_command, shell=True, capture_output=True, text=True, check=True
                    )
                    kill_command = f"ps -aux | grep {process} | grep -v grep | awk '{{print $2}}' | xargs kill"
            except Exception as e:
                console.print(f"[bold red]{process} already dead[/]")



def shut_down(settings, name, pid):
    console.print(f"Shutting down {name} with PID {pid}")
    if pid:
        try:
            # Terminate the process
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            print(f"Process with PID {pid} does not exist.")
        except PermissionError:
            print(f"Permission denied to kill process with PID {pid}.")
        except Exception as e:
            print(f"An error occurred: {e}")



def log_dir(settings:JitSettings):
    if not settings.log_dir:
        # Define default LOG_DIR if not set
        settings.log_dir = f"logs_nodes{settings.nodes}_Jobid{settings.job_id}"

    # Create directory if it does not exist
    os.makedirs(settings.log_dir, exist_ok=True)

    # Resolve and return the absolute path of LOG_DIR
    settings.log_dir = os.path.abspath(settings.log_dir)
    settings.set_log_dirs()


def get_address_ftio(settings: JitSettings) -> None:
    # Get Address and port
    jit_print("####### Getting FTIO ADDRESS")
    if settings.cluster:
        call = f"srun --jobid={settings.job_id} {settings.ftio_node_command} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ip addr | grep ib0 | awk '{{print $2}}' | cut -d'/' -f1 | tail -1"
        jit_print(f"[bold cyan]>> Executing: {call}")
        try:
            result = subprocess.run(
                call, shell=True, capture_output=True, text=True, check=True
            )
            settings.address_ftio = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            jit_print(f"[bold red]>>Error occurred: {e}")
            settings.address_ftio = ""

    jit_print(f">> Address FTIO: {settings.address_ftio}")


def get_address_cargo(settings: JitSettings) -> None:
    jit_print("####### Getting Cargo ADDRESS")
    if settings.cluster:
        call = f"srun --jobid={settings.job_id} {settings.single_node_command} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ip addr | grep ib0 | awk '{{print $2}}' | cut -d'/' -f1 | tail -1"
        jit_print(f"[bold cyan]>> Executing: {call}")
        try:
            result = subprocess.run(
                call, shell=True, capture_output=True, text=True, check=True
            )
            settings.address_cargo = result.stdout.strip()
            settings.cargo_server = f"ofi+sockets://{settings.address_cargo}:62000"
        except subprocess.CalledProcessError as e:
            jit_print(f"[bold red]>>Error occurred: {e}")
            settings.address_cargo = ""
            settings.cargo_server = ""
    else:
        settings.cargo_server = f"ofi+tcp://{settings.address_cargo}:62000"

    jit_print(f">> Address CARGO: {settings.address_cargo}")
    jit_print(f">> CARGO server:  {settings.cargo_server} ")


def print_settings(settings) -> None:
    ftio_status = f"[bold green]ON[/]"
    gkfs_demon_status = f"[bold green]ON[/]"
    gkfs_proxy_status = f"[bold green]ON[/]"
    cargo_status = f"[bold green]ON[/]"

    # Default settings text
    ftio_text = f"""
├─ ftio activate  : {settings.ftio_activate}
├─ address ftio   : {settings.address_ftio}
├─ port           : {settings.port}
├─ # nodes        : 1
└─ ftio node      : {settings.ftio_node_command.replace('--nodelist=', '')}"""

    gkfs_demon_text = f"""
├─ gkfs demon     : {settings.gkfs_demon}
├─ gkfs intercept : {settings.gkfs_intercept}
├─ gkfs mntdir    : {settings.gkfs_mntdir}
├─ gkfs rootdir   : {settings.gkfs_rootdir}
├─ gkfs hostfile  : {settings.gkfs_hostfile}"""

    gkfs_proxy_text = f"""
├─ gkfs proxy     : {settings.gkfs_proxy}
└─ gkfs proxyfile : {settings.gkfs_proxyfile}"""

    cargo_text = f"""
├─ cargo          : {settings.cargo}
├─ cargo cli      : {settings.cargo_cli}
├─ stage in path  : {settings.stage_in_path}
└─ address cargo  : {settings.address_cargo}"""

    if settings.exclude_ftio:
        ftio_text = """
├─ ftio activate  : [yellow]none[/]
├─ address ftio   : [yellow]none[/]
├─ port           : [yellow]none[/]
├─ # nodes        : [yellow]none[/]
└─ ftio node      : [yellow]none[/]"""
        ftio_status = "[bold yellow]off[/]"

    if settings.exclude_demon:
        gkfs_demon_text = """
├─ gkfs demon     : [yellow]none[/]
├─ gkfs intercept : [yellow]none[/]
├─ gkfs mntdir    : [yellow]none[/]
├─ gkfs rootdir   : [yellow]none[/]
├─ gkfs hostfile  : [yellow]none[/]"""
        gkfs_demon_status = "[bold yellow]off[/]"

    if settings.exclude_proxy:
        gkfs_proxy_text = """
├─ gkfs proxy     : [yellow]none[/]
└─ gkfs proxyfile : [yellow]none[/]"""
        gkfs_proxy_status = "[bold yellow]off[/]"

    if settings.exclude_cargo:
        cargo_text = """
├─ cargo location : [yellow]none[/]
├─ cargo cli      : [yellow]none[/]
├─ stage in path  : [yellow]none[/]
└─ address cargo  : [yellow]none[/]"""
        cargo_status = "[bold yellow]off[/]"

    # print settings
    text = f"""
[bold green]Settings
##################[/]
[bold green]setup[/]
├─ logs dir       : {settings.log_dir}
├─ pwd            : {os.getcwd()}
├─ ftio           : {ftio_status}
├─ gkfs demon     : {gkfs_demon_status}
├─ gkfs proxy     : {gkfs_proxy_status}
├─ cargo          : {cargo_status}
├─ cluster        : {settings.cluster}
├─ total nodes    : {settings.nodes}
|   ├─ app        : {settings.app_nodes}
|   └─ ftio       : 1
├─ procs          : {settings.procs}
|   ├─ app        : {settings.procs_app}
|   ├─ demon      : {settings.procs_demon}
|   ├─ proxy      : {settings.procs_proxy}
|   ├─ cargo      : {settings.procs_cargo}
|   └─ ftio       : {settings.procs_ftio}
├─ max time       : {settings.max_time}
└─ job id         : {settings.job_id}

[bold green]ftio[/]{ftio_text}

[bold green]gekko[/]{gkfs_demon_text}{gkfs_proxy_text}

[bold green] cargo[/]{cargo_text}

[bold green]app[/]
├─ precall        : {settings.precall}
├─ app_call       : {settings.app_call}
├─ # nodes        : {settings.app_nodes}
└─ app nodes      : {settings.app_nodes_command.replace('--nodelist=', '')}
[bold green]##################[/]
"""
    console.print(text)
    print_to_file(text, os.path.join(settings.log_dir, "settings.log"))


def print_to_file(text, file):
    remove = ["bold", "green", "yellow", "red", "cyan", "[/]", "[ ]", "[]"]
    for r in remove:
        text = text.replace(r, "")

    with open(file, "w") as file:
        file.write(text)


def jit_print(s: str):
    console.print(f"[bold green]JIT[/][green] {s}[/]")



def create_hostfile(settings):
    jit_print(f"[cyan]>> Cleaning Hostfile: {settings.gkfs_hostfile}")

    try:
        if os.path.exists(settings.gkfs_hostfile):
            os.remove(settings.gkfs_hostfile)
        else:
            jit_print("[blue]>> No hostfile found[/blue]")

    except Exception as e:
        jit_print(f"[bold red]Error removing hostfile:[/bold red] {e}")

    # # Optionally, recreate the hostfile and populate it if needed
    # try:
    #     # Create the hostfile (if needed)
    #     # with open(settings.gkfs_hostfile, 'w') as file:
    #     #     for node in settings.nodes_arr[:-1]:  # Exclude the last element
    #     #         file.write(f"cpu{node}\n")
    #     # console.print(f"[cyan]>> Creating Hostfile: {settings.gkfs_hostfile}")
    #     pass
    # except Exception as e:
    #     console.print(f"[bold red]Error creating hostfile:[/bold red] {e}")


def format_time(elapsed):
    """Format the elapsed in a more readable way."""
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {seconds:.2f}s"


def elapsed_time(settings: JitSettings, runtime:JitTime, name, elapsed):
    """Calculate and print the elapsed time."""

    elapsed_formatted = format_time(elapsed)
    log_message = (
        f"\n\n[cyan]############[JIT]##############\n"
        f"# {name}\n"
        f"# time: [yellow]{elapsed_formatted} [cyan]\n"
        f"# [yellow]{elapsed} [cyan]seconds\n"
        f"##############################\n\n"
    )
    console.print(log_message)

    # Write to log file
    print_to_file(
        log_message,
        os.path.join(settings.log_dir, "time.log"),
    )

    if "stage" in name.lower():
        if "in" in name .lower():
            runtime.stage_in = elapsed
        elif "out" in name.lower():
            runtime.stage_out = elapsed
    elif "app" in name.lower():
        runtime.app = elapsed


def check(settings: JitSettings):
    try:
        files = subprocess.check_output(
            f"LD_PRELOAD={settings.gkfs_intercept} LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} ls {settings.gkfs_mntdir}",
            shell=True,
            text=True,
        )
        jit_print(f"[cyan]>> geko_ls {settings.gkfs_mntdir}: [/]\n{files}")
    except subprocess.CalledProcessError as e:
        jit_print(f"[red]>> Failed to list files in {settings.gkfs_mntdir}: {e}[/]")


def update_hostfile_mpi(settings:JitSettings):
        # Command to get the list of hostnames for the job
    squeue_command = f"squeue -j {settings.job_id} -o '%N' | tail -n +2"
    scontrol_command = f"scontrol show hostname $({squeue_command})"
    
    # Execute the command and capture the hostnames
    hostnames = subprocess.check_output(scontrol_command, shell=True).decode().splitlines()

    # Path to the output file
    hostfile_mpi_path = os.path.expanduser("~/hostfile_mpi")
    
    # Write the hostnames to the file, excluding the Ftio node
    with open(hostfile_mpi_path, 'w') as hostfile:
        for hostname in hostnames:
            if hostname.strip() != settings.ftio_node:
                hostfile.write(hostname + '\n')