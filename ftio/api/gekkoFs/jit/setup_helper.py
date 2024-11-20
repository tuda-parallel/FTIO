import sys
import subprocess
import getopt
import os
import signal
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
            jit_print(
                f"[bold red]>> Error: Port {port_number} is already in use...[/bold red]"
            )
            return True  # Port is in use
    except subprocess.CalledProcessError:
        # grep returns a non-zero exit status if it finds no matches
        jit_print(f"[bold blue]>> Port {port_number} is available.[/bold blue]")
        return False  # Port is free


def check_port(settings: JitSettings):
    """Check if a port is available and terminate any existing process using it."""
    if is_port_in_use(settings.port):
        jit_print(
            f"[bold red]>> Error: Port {settings.port} is already in use on {settings.address_ftio}. Terminating existing process...[/]"
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
                jit_print(
                    f"[bold yellow]>> Terminating process with PID: {process_id}[/]"
                )
                os.kill(int(process_id), 9)
                jit_print(
                    f"[bold green]>> Using port {settings.port} on {settings.address_ftio}.[/]"
                )
                return 0
            else:
                jit_print(
                    f">>[bold red]>> Failed to identify process ID for PORT {settings.port}.[/]"
                )
                exit(1)
        except subprocess.CalledProcessError as e:
            jit_print(f"[bold red]>> Failed to retrieve process information: {e}[/]")
            exit(1)
    else:
        jit_print(
            f"[bold green]>> Using port {settings.port} on {settings.address_ftio}.[/]"
        )


def parse_options(settings: JitSettings, args: list) -> None:

    try:
        opts, args = getopt.getopt(
            args,
            "a:r:n:p:c:o:t:j:l:i:e:xdvyuh",
            [
                "address=",
                "port=",
                "nodes=",
                "total_procs=",
                "procs_list=",
                "omp_threads=",
                "max-time=",
                "job-id=",
                "log-name=",
                "install_location=",
                "exclude=",
                "exclude-all",
                "dry_run",
                "verbose",
                "skip_confirm",
                "use-mpirun",
                "help",
            ],
        )
    except getopt.GetoptError as err:
        console.print(f"[bold red]Error: {err}[/bold red]")
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-a", "--address"):
            settings.address_ftio = arg
        elif opt in ("-r", "--port"):
            settings.port = arg
        elif opt in ("-n", "--nodes"):
            settings.nodes = int(arg)
        elif opt in ("-t", "--max-time"):
            settings.max_time = int(arg)
        elif opt in ("-j", "--job-id"):
            settings.job_id = int(arg)
            settings.static_allocation = True
        elif opt in ("-l", "--log-name"):
            settings.log_dir = arg
        elif opt in ("-i", "--install_location"):
            settings.install_location = arg
            install_all(settings)
        elif opt in ("-c", "--total_procs"):
            settings.procs = int(arg)
        elif opt in ("-o", "--omp_threads"):
            settings.omp_threads = int(arg)
        elif opt in ("-p", "--procs_list"):
            # Split the argument by comma to get the list of numbers
            procs_list = arg.split(",")
            try:
                procs_list = [int(proc) for proc in procs_list]
            except ValueError:
                console.print(
                    "[bold red]Invalid --procs value. It must be a comma-separated list of numbers.[/]"
                )
                sys.exit(1)

            # Check the number of elements and assign accordingly
            if len(procs_list) > 5:
                console.print("[bold red]Too many values for --procs. Maximum is 5.[/]")
                sys.exit(1)
            elif len(procs_list) > 0:
                settings.procs_app = int(procs_list[0])
            if len(procs_list) > 1:
                settings.procs_daemon = int(procs_list[1])
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
                    if exclude.lower() == "ftio":
                        settings.exclude_ftio = True
                        console.print("[yellow]- ftio[/]")
                    elif exclude.lower() == "cargo":
                        settings.exclude_cargo = True
                        console.print("[yellow]- cargo[/]")
                    elif exclude.lower() in ("gkfs", "daemon", "proxy"):
                        if exclude.lower() == "gkfs":
                            settings.exclude_daemon = True
                            settings.exclude_proxy = True
                            console.print("[yellow]- gkfs[/]")
                        elif exclude.lower() == "daemon":
                            settings.exclude_daemon = True
                            console.print("[yellow]- daemon[/]")
                        elif exclude.lower() == "proxy":
                            settings.exclude_proxy = True
                            console.print("[yellow]- proxy[/]")
                    elif exclude.lower() == "all":
                        settings.exclude_all = True
                        console.print("[yellow]- all[/]")
                    else:
                        jit_print(f"[bold red]>> Invalid exclude option: {exclude} [/]")
                        sys.exit(1)
        elif opt in ("-x", "--exclude-all"):
            settings.exclude_all = True
        elif opt in ("-d", "--dry_run"):
            settings.dry_run = True
        elif opt in ("-v", "--verbose"):
            settings.verbose = True
        elif opt in ("-y", "--skip_confirm"):
            settings.skip_confirm = True
        elif opt in ("-u", "--use-mpirun"):
            settings.use_mpirun = True
        elif opt in ("-h", "--help"):
            error_usage(settings)
            sys.exit(1)

        else:
            jit_print(f"[bold red]>>Invalid option: {opt}[/]")
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

    -r | --port: XXXX <int>
        default: [bold yellow]{settings.port}[/]
        port for FTIO and GekkoFS.

    -n | --nodes: X <int>
        default: [bold yellow]{settings.nodes}[/]
        number of nodes to run the setup. In cluster mode, FTIO is 
        executed on a single node, while the rest (including the
        application) get X-1 nodes.

    -c | --total_procs: X <int>
        default: [bold yellow]{settings.procs}[/]
        if procs_list is skipped, this is the default number of procs assigned to all
        
    -p | --procs_list: x,x,..,x <list>
        default: [bold yellow]{settings.procs_app},{settings.procs_daemon},{settings.procs_proxy},{settings.procs_cargo},{settings.procs_ftio}[/]
        List of task per node/cpu per proc for app, daemon, proxy, cargo, and ftio, respectively.
        Assignment is from right to left depending on the length of the list.
        FTIO, GekkoFS (proxy and daemon) always have 1 task per node. The 
        assignment in this list specifics the cpu per task. For cargo and the app, the task per node
        is calculated as nodes*procs_cargo or nodes*procs_app, respectively.

    -o | --omp_threads: X <int>
        default: [bold yellow]{settings.omp_threads}[/]
        OpenMP threads used

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
        Supported options include: ftio, daemon, proxy, gkfs (daemon + proxy), 
        cargo, and all (same as -x).

    -x | --exclude-all
        default: [bold yellow]{settings.exclude_all}[/]
        If this flag is provided, the setup is executed without FTIO, 
        GekkoFs, and Cargo.


    -d | --dry_run 
        default: [bold yellow]{settings.dry_run}[/]
        If provided, the tools and the app are not executed

    -v | --verbose
        default: [bold yellow]{settings.verbose}[/]
        If provided, the tools output of each step is shown

    -y | --skip_confirm 
        default: [bold yellow]{settings.skip_confirm}[/]
        If this flag is provided, the setup automatically cancels running jobs 
        name JIT

    -u | --use-mpirun
        default: [bold yellow]{settings.use_mpirun}[/]
        If this flag is provided, the setup avoids using srun and 
        uses mpirun. Use -j JobID in combination with this flag, as 
        all calls are executed with the assumption you already 
        ssh to the host

    -i | --install_location: full_path <str>
        default: [bold yellow]{settings.install_location}[/]
        Installs everything in the provided directory.

---- exit ----
    """
    )


def abort():
    jit_print("[bold red] >>> Aborting installation[/]")
    exit(1)


def install_all(settings: JitSettings) -> None:
    with console.status("[bold green]Starting installation...") as status:
        try:
            # Create directory
            jit_print(">>> Creating directory")
            status.update("[bold green]JIT >>> Creating directory[/]", speed=30)
            os.makedirs(settings.install_location, exist_ok=True)

            # unload CUDA for Gekko
            command = 'module -t list 2>&1 | grep -q "CUDA" && module unload $(module -t list 2>&1 | grep "CUDA")'
            try:
                # Execute the bash command
                subprocess.run(command, shell=True, check=True)
                jit_print(">>> CUDA module unloaded successfully.")
            except subprocess.CalledProcessError:
                jit_print(">>> CUDA module not found or failed to unload.")

            # Clone GKFS
            jit_print(">>> Installing GKFS")
            if os.path.isdir(os.path.join(settings.install_location, "gekkofs")):
                jit_print(">>> GKFS exists, skipping installation")
            else:
                status.update("[bold green]JIT >>> Installing GKFS[/]", speed=30)
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
                jit_print(">>> Building GKFS")
                status.update("[bold green]JIT >>> Building GKFS[/]", speed=30)
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
                subprocess.run(
                    ["make", "-j", "4", "install"], cwd=build_dir, check=True
                )

                jit_print(">>> GEKKO installed")
                status.update("[bold green]JIT >>> GEKKO installed[/]", speed=30)

            jit_print(">>> Installing Boost")
            status.update("[bold green]JIT >>> Getting Boost[/]", speed=30)
            if os.path.isfile(
                os.path.join(settings.install_location, "boost_1_84_0.tar.gz")
            ):
                print("File exists.")
                jit_print(">>> Boost tar exists, skipping download")
            else:
                try:
                    subprocess.run(
                        [
                            "wget",
                            "https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.gz",
                        ],
                        cwd=settings.install_location,
                        check=True,
                    )
                except:
                    jit_print(">>> Wget failed, copying boost from shared")
                    subprocess.run(
                        [
                            "cp",
                            "/lustre/project/nhr-admire/shared/boost_1_84_0.tar.gz",
                            ".",
                        ],
                        cwd=settings.install_location,
                        check=True,
                    )
            if os.path.isdir(os.path.join(settings.install_location, "boost_1_84_0")):
                jit_print(">>> Boost exists, skipping installation")
            else:
                status.update(
                    "[bold green]JIT >>> Extracting boost from tar archive [/]",
                    speed=30,
                )
                subprocess.run(
                    ["tar", "-xzf", "boost_1_84_0.tar.gz"],
                    cwd=settings.install_location,
                    check=True,
                )
                status.update(
                    "[bold green]JIT >>> Installing Boost: bootstrap[/]", speed=30
                )
                build_dir = os.path.join(settings.install_location, "boost_1_84_0")
                os.chdir(build_dir)
                subprocess.run(f"{build_dir}/bootstrap.sh", cwd=build_dir, check=True)
                status.update(
                    "[bold green]JIT >>> Installing Boost: b2 install[/]", speed=30
                )
                subprocess.run(
                    [
                        f"{build_dir}/b2",
                        "install",
                        f"--prefix={settings.install_location}/iodeps",
                        "toolset=gcc",
                    ],
                    cwd=build_dir,
                    check=True,
                )
                status.update(
                    "[bold green]JIT >>> Installing Boost: b2 headers[/]", speed=30
                )
                subprocess.run(
                    [
                        f"{build_dir}/b2",
                        "headers",
                        f"--prefix={settings.install_location}/iodeps",
                    ],
                    cwd=build_dir,
                    check=True,
                )
                jit_print(">>> Boost installed")
                os.chdir(settings.install_location)
                status.update("[bold green]JIT >>> Boost installed[/]", speed=30)

            jit_print(">>> Installing Cereal")
            status.update("[bold green]JIT >>> Installing Cereal[/]", speed=30)
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
            jit_print(">>> Cereal installed")
            status.update("[bold green]JIT >>> Cereal installed[/]", speed=30)

            # Install Cargo Dependencies: Thallium
            jit_print(">>> Installing Thallium")
            status.update("[bold green]JIT >>> Installing Thallium[/]", speed=30)
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
            jit_print(">>> Mochi-thallium installed")
            status.update("[bold green]JIT >>> Mochi-thallium installed[/]", speed=30)

            # Clone and Build Cargo
            jit_print(">>> Installing Cargo")
            status.update("[bold green]JIT >>> Installing Cargo[/]", speed=30)
            subprocess.run(
                ["git", "clone", "https://storage.bsc.es/gitlab/hpc/cargo.git"],
                cwd=settings.install_location,
                check=True,
            )
            os.chdir(os.path.join(settings.install_location, "cargo"))
            replace_line_in_file(
                "src/master.cpp", 332, f'  auto patternFile = "{settings.regex_file}";'
            )
            subprocess.run(
                ["git", "checkout", "marc/nek5000"],
                check=True,
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

            jit_print(">>> Cargo installed")
            status.update("[bold green]JIT >>> Cargo installed[/]", speed=30)

            # Build IOR
            jit_print(">>> Installing IOR")
            status.update("[bold green]JIT >>> Installing IOR[/]", speed=30)
            subprocess.run(
                ["git", "clone", "https://github.com/hpc/ior.git"],
                cwd=settings.install_location,
                check=True,
            )
            os.chdir(os.path.join(settings.install_location, "ior"))
            subprocess.run(["./bootstrap"], check=True)
            subprocess.run(["./configure"], check=True)
            subprocess.run(["make", "-j", "4"], check=True)

            jit_print(">> Installation finished")
            status.update("[bold green]JIT >> Installation finished[/]", speed=30)
            console.print("\n>> Ready to go <<")
            status.update("\n>> Ready to go <<", speed=30)
            console.print("Call: ./jit.sh -n NODES -t MAX_TIME")
            status.update("Call: ./jit.sh -n NODES -t MAX_TIME", speed=30)

        except subprocess.CalledProcessError as e:
            jit_print(f"[bold red] >>> Error encountered: {e}[/]")
            status.update(
                "[bold green]JIT [bold red] >>> Error encountered: {e}[/]", speed=30
            )
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


def cancel_jit_jobs(settings: JitSettings):
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
            jit_print(
                "[bold yellow]>> The following jobs with the name 'JIT' were found:[/]"
            )
            console.print(job_list)

            if not settings.skip_confirm:
                # Prompt the user to confirm cancellation
                confirmation = (
                    input("Do you want to cancel all 'JIT' jobs? (yes/no): ")
                    .strip()
                    .lower()
                )
            else:
                confirmation = "yes"

            if confirmation in {"yes", "y", "ye"}:
                for job_id in jit_jobs:
                    subprocess.run(f"scancel {job_id}", shell=True, check=True)
                    jit_print(f"[bold cyan]>> Cancelled job ID {job_id}[/]")
                jit_print("[bold green]>> All 'JIT' jobs have been cancelled[/]")
            else:
                jit_print("[bold yellow]>> No jobs were cancelled[/]")


def relevant_files(settings: JitSettings):

    if settings.verbose:  # Mimicking checking for the number of arguments
        jit_print(f"[cyan]>> Setting up ignored files[/]")

    # Create or update the regex file with the settings.regex_match
    with open(settings.regex_file, "w") as file:
        file.write(f"{settings.regex_match}\n")

    if settings.verbose:
        jit_print(f"[cyan]>> Files that match {settings.regex_match} are ignored [/]")

    # Display the contents of the regex file
    with open(settings.regex_file, "r") as file:
        content = file.read()
    if settings.verbose:
        jit_print(f"[cyan]>> content of {settings.regex_file}: \n{content}[/]")


def reset_relevant_files(settings: JitSettings) -> None:
    if settings.cluster:
        jit_print(f"[cyan]>> Resetting ignored files[/]")
        # Write the default regex pattern to the file
        settings.regex_match = ".*"
        with open(settings.regex_file, "w") as file:

            file.write(f"{settings.regex_match}\n")
        # Optionally jit_print the contents of the regex file
        # with open(settings.regex_file, 'r') as file:
        #     content = file.read()
        # jit_print(f"[bold cyan]>> cat {settings.regex_file}: \n{content} [/]\n")


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

    if settings.use_mpirun and settings.job_id == 0:
        jit_print(
            " [bold yellow]>> Warning, executing mpiexec on remote. We advice using using fixed allocation with mpirun\n"
        )

    if settings.cluster:
        # allocate if needed
        if settings.job_id == 0:
            # Allocating resources
            jit_print("[green] ####### Allocating resources[/]")

            call = f"salloc -N {settings.nodes} -t {settings.max_time} {settings.alloc_call_flags}"
            jit_print(f"[cyan] >> Executing: {call} [/]")
            # Execute the salloc command
            subprocess.run(call, shell=True, check=True)

            # Get JIT_ID
            try:
                result = subprocess.run(
                    f"squeue -o '%.18i %.9P %.8j %.8u %.2t %.10M %.6D %R' | grep '{settings.job_name}' | sort -k1,1rn | head -n 1 | awk '{{print $1}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                settings.job_id = int(result.stdout.strip())
            except subprocess.CalledProcessError:
                settings.job_id = 0
        else:
            console.print(
                f"[bold green]JIT [green] ####### Using allocation with id: {settings.job_id}[/]"
            )

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
                # console.print(f"[bold green] ## Node res {nodes_result}[/]")
                # console.print(f"[bold green] ## Node res stdout{nodes_result.stdout}[/]")
                # console.print(f"[bold green] ## Node arr {nodes_arr}[/]")
                # console.print(f"[bold green] ## split{nodes_result.stdout.split()}[/]")
                if nodes_arr:
                    try:
                        nodes_arr = nodes_arr[: int(settings.nodes)]
                    except Exception as e:
                        print(e)
                        console.print(
                            f"[bold green]JIT [red] >> Unable to decrease number of nodes. Using {settings.nodes}[/]"
                        )
            except subprocess.CalledProcessError:
                nodes_arr = []

            # Write to hostfile_mpi
            with open(f"{settings.dir}/hostfile_mpi", "w") as file:
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
                    # print(nodes_arr)
                    # print(f"{','.join(n for n in nodes_arr if n != settings.ftio_node)}\n")

                    # Remove FTIO node from hostfile_mpi
                    with open(f"{settings.dir}/hostfile_mpi", "r") as file:
                        lines = file.readlines()
                    with open(f"{settings.dir}/hostfile_mpi", "w") as file:
                        file.writelines(
                            line for line in lines if line.strip() != settings.ftio_node
                        )

                jit_print(f"[green]>> JIT Job Id: {settings.job_id} [/]")
                jit_print(f"[green]>> Allocated Nodes: {len(nodes_arr)} [/]")
                jit_print(f"[green]>> FTIO Node: {settings.ftio_node} [/]")
                jit_print(
                    f"[green]>> APP Node command: {settings.app_nodes_command} [/]"
                )
                jit_print(
                    f"[green]>> FTIO Node command: {settings.ftio_node_command} [/]"
                )

                # Print contents of hostfile_mpi
                with open(f"{settings.dir}/hostfile_mpi", "r") as file:
                    hostfile_content = file.read()
                jit_print(
                    f"[cyan]>> content of {settings.dir}/hostfile_mpi: \n{hostfile_content} [/]"
                )
            settings.update_geko_files()
        else:
            jit_print("[bold red]>> JOB ID could not be retrieved[/]")


def get_pid(settings: JitSettings, name: str, pid: int):
    if settings.cluster:
        call = f"ps aux | grep 'srun' | grep '{settings.job_id}' | grep '{name}' | grep -v grep | tail -1 | awk '{{print $2}}'"
        res = subprocess.run(
            call, shell=True, check=True, capture_output=True, text=True
        )
        if res.stdout.strip():
            try:
                pid = int(res.stdout.strip())
            except:
                pid = res.stdout.strip()

    if name.lower() in "cargo":
        settings.cargo_pid = pid
        jit_print(f">> Cargo startup successful. PID is {pid}")
    elif name.lower() in "gkfs_daemon":
        settings.gekko_daemon_pid = pid
        jit_print(f">> Gekko daemon startup successful. PID is {pid}")
    elif name.lower() in "gkfs_proxy":
        settings.gekko_proxy_pid = pid
        jit_print(f">> Gekko proxy startup successful. PID is {pid}")
    elif name.lower() in "ftio" or name.lower() in "predictor_jit":
        settings.ftio_pid = pid
        jit_print(f">> FTIO startup successful. PID is {pid}")


def handle_sigint(settings: JitSettings):
    if settings.trap_exit:
        settings.trap_exit = False
        jit_print("[bold blue]>> Keyboard interrupt detected. Exiting script.[/]")
        info = (
            f"{settings.app_call} with {settings.nodes} nodes ({settings.log_suffix})"
        )
        jit_print(f"[bold blue]>> Killing Job: {info}.\n Exiting script.[/]")
        log_failed_jobs(settings, info)
        soft_kill(settings)
        hard_kill(settings)
        jit_print(">> Exciting\n")
        sys.exit(0)


def soft_kill(settings: JitSettings) -> None:
    if settings.soft_kill:
        jit_print("[bold green]####### Soft kill [/]", True)

        if not settings.exclude_ftio:
            try:
                shut_down(settings, "FTIO", settings.ftio_pid)
                jit_print("[bold cyan] >> killed FTIO [/]")
            except:
                jit_print("[bold cyan] >> Unable to soft kill FTIO [/]")

    if not settings.exclude_daemon:
        try:
            shut_down(settings, "GEKKO", settings.gekko_daemon_pid)
            jit_print("[bold cyan] >> killed GEKKO DEMON [/]")
        except:
            jit_print("[bold cyan] >> Unable to soft kill GEKKO DEMON [/]")

    if not settings.exclude_proxy:
        try:
            shut_down(settings, "GEKKO", settings.gekko_proxy_pid)
            jit_print("[bold cyan] >> killed GEKKO PROXY [/]")
        except:
            jit_print("[bold cyan] >> Unable to soft  kill GEKKO PROXY [/]")

    if not settings.exclude_cargo:
        try:
            shut_down(settings, "CARGO", settings.cargo_pid)
            jit_print("[bold cyan] >> killed CARGO [/]")
        except:
            jit_print("[bold cyan] >> Unable to soft kill CARGO [/]")

    jit_print(">> Soft kill finished")


def hard_kill(settings) -> None:
    if settings.hard_kill:
        jit_print(f"[bold green]####### Hard kill[/]", True)

        if settings.cluster and not settings.static_allocation:
            # Cluster environment: use `scancel` to cancel the job
            _ = subprocess.run(
                f"scancel {settings.job_id}",
                shell=True,
                text=True,
                capture_output=True,
                check=True,
                executable="/bin/bash",
            )
        else:
            # Non-cluster environment: use `kill` to terminate processes
            processes = [
                settings.gkfs_daemon,
                settings.gkfs_proxy,
                settings.cargo,
                f"{settings.ftio_bin_location}/predictor_jit",
            ]

            for process in processes:
                try:
                    # Find process IDs and kill them
                    kill_command = f"ps -aux | grep {process} | grep -v grep | awk '{{print $2}}' | xargs kill"
                    while kill_command:
                        _ = subprocess.run(
                            kill_command,
                            shell=True,
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        kill_command = f"ps -aux | grep {process} | grep -v grep | awk '{{print $2}}' | xargs kill"
                except Exception as e:
                    console.print(f"[bold red]{process} already dead[/]")

        jit_print(">> Hard kill finished")


def shut_down(settings: JitSettings, name, pid):
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


def log_dir(settings: JitSettings):
    if not settings.log_dir:
        # Define default LOG_DIR if not set
        settings.log_dir = f"logs_nodes{settings.nodes}_Jobid{settings.job_id}"
        # settings.gkfs_mntdir = f"{settings.gkfs_mntdir}_Jobid{settings.job_id}"
        # settings.gkfs_rootdir = f"{settings.gkfs_rootdir}_Jobid{settings.job_id}"

        if settings.log_suffix:
            settings.log_dir += f"_{settings.log_suffix}"

    counter = 0
    while os.path.exists(settings.log_dir):
        counter += 1
        settings.log_dir = f"{settings.log_dir}_{counter}"

    # Resolve and return the absolute path of LOG_DIR
    settings.log_dir = os.path.abspath(settings.log_dir)

    # Create directory if it does not exist
    os.makedirs(settings.log_dir, exist_ok=True)

    settings.set_log_dirs()


def get_address_ftio(settings: JitSettings) -> None:
    # Get Address and port
    jit_print(">> Getting FTIO ADDRESS")
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

    jit_print(f">> Address FTIO: {settings.address_ftio}", True)


def get_address_cargo(settings: JitSettings) -> None:
    jit_print(">> Getting Cargo ADDRESS")
    if settings.cluster:
        call = f"srun --jobid={settings.job_id} {settings.single_node_command} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ip addr | grep ib0 | awk '{{print $2}}' | cut -d'/' -f1 | tail -1"
        jit_print(f"[bold cyan]>> Executing: {call}")
        try:
            result = subprocess.run(
                call, shell=True, capture_output=True, text=True, check=True
            )
            settings.address_cargo = result.stdout.strip()
            settings.cargo_server = (
                f"{settings.gkfs_daemon_protocol}://{settings.address_cargo}:62000"
            )
        except subprocess.CalledProcessError as e:
            jit_print(f"[bold red]>>Error occurred: {e}")
            settings.address_cargo = ""
            settings.cargo_server = ""
    else:
        settings.cargo_server = f"ofi+tcp://{settings.address_cargo}:62000"

    jit_print(f">> Address CARGO: {settings.address_cargo}")
    jit_print(f">> CARGO server:  {settings.cargo_server} ", True)


def set_dir_gekko(settings: JitSettings) -> None:
    if settings.node_local and settings.cluster:
        jit_print(">> Setting Gekko root dir to node local")
        settings.gkfs_rootdir = (
            f"/localscratch/{settings.job_id}/{os.path.basename(settings.gkfs_rootdir)}"
        )
        settings.gkfs_mntdir = (
            f"/localscratch/{settings.job_id}/{os.path.basename(settings.gkfs_mntdir)}"
        )
        jit_print(
            f">> Gekko root dir set to: {settings.gkfs_rootdir}\n>> Gekko mnt dir set to: {settings.gkfs_mntdir}",
            True,
        )


def print_settings(settings) -> None:
    # Default values
    ftio_status = f"[bold green]ON[/]"
    gkfs_daemon_status = f"[bold green]ON[/]"
    gkfs_proxy_status = f"[bold green]ON[/]"
    cargo_status = f"[bold green]ON[/]"

    task_daemon = f"{settings.app_nodes}"
    cpu_daemon = f"{settings.procs_daemon}"
    task_proxy = f"{settings.app_nodes}"
    cpu_proxy = f"{settings.procs_proxy}"
    task_cargo = f"{settings.app_nodes*settings.procs_cargo}"
    cpu_cargo = f"{settings.procs_cargo}"
    task_ftio = "1"
    cpu_ftio = f"{settings.procs_ftio}"

    # Default settings text
    ftio_text = f"""
├─ ftio location  : {settings.ftio_bin_location}
├─ address ftio   : {settings.address_ftio}
├─ port           : {settings.port}
├─ # nodes        : 1
└─ ftio node      : {settings.ftio_node_command.replace('--nodelist=', '')}"""

    gkfs_daemon_text = f"""
├─ gkfs daemon    : {settings.gkfs_daemon}
├─ gkfs intercept : {settings.gkfs_intercept}
├─ gkfs mntdir    : {settings.gkfs_mntdir}
├─ gkfs rootdir   : {settings.gkfs_rootdir}
├─ gkfs hostfile  : {settings.gkfs_hostfile}"""

    gkfs_proxy_text = f"""
├─ gkfs proxy     : {settings.gkfs_proxy}
└─ gkfs proxyfile : {settings.gkfs_proxyfile}"""

    cargo_text = f"""
├─ cargo          : {settings.cargo}
├─ cargo cli      : {settings.cargo_bin}
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
        task_ftio = "[bold yellow]-[/]"
        cpu_ftio = "[bold yellow]-[/]"

    if settings.exclude_daemon:
        gkfs_daemon_text = """
├─ gkfs daemon    : [yellow]none[/]
├─ gkfs intercept : [yellow]none[/]
├─ gkfs mntdir    : [yellow]none[/]
├─ gkfs rootdir   : [yellow]none[/]
├─ gkfs hostfile  : [yellow]none[/]"""
        gkfs_daemon_status = "[bold yellow]off[/]"
        task_daemon = "[bold yellow]-[/]"
        cpu_daemon = "[bold yellow]-[/]"

    if settings.exclude_proxy:
        gkfs_proxy_text = """
├─ gkfs proxy     : [yellow]none[/]
└─ gkfs proxyfile : [yellow]none[/]"""
        gkfs_proxy_status = "[bold yellow]off[/]"
        task_proxy = "[bold yellow]-[/]"
        cpu_proxy = "[bold yellow]-[/]"

    if settings.exclude_cargo:
        cargo_text = """
├─ cargo location : [yellow]none[/]
├─ cargo cli      : [yellow]none[/]
├─ stage in path  : [yellow]none[/]
└─ address cargo  : [yellow]none[/]"""
        cargo_status = "[bold yellow]off[/]"
        task_cargo = "[bold yellow]-[/]"
        cpu_cargo = "[bold yellow]-[/]"

    # print settings
    text = f"""
[bold green]Settings
##################[/]
[bold green]setup[/]
├─ logs dir       : {settings.log_dir}
├─ pwd            : {settings.dir}
├─ ftio           : {ftio_status}
├─ gkfs daemon    : {gkfs_daemon_status}
├─ gkfs proxy     : {gkfs_proxy_status}
├─ cargo          : {cargo_status}
├─ cluster        : {settings.cluster}
├─ total nodes    : {settings.nodes}
|   ├─ app        : {settings.app_nodes}
|   └─ ftio       : 1
├─ tasks per node : -  
|   ├─ app        : {settings.procs_app} 
|   ├─ daemon     : {task_daemon}
|   ├─ proxy      : {task_proxy}
|   ├─ cargo      : {task_cargo}
|   └─ ftio       : {task_ftio}
├─ cpus per task  : {settings.procs} 
|   ├─ app        : 1
|   ├─ daemon     : {cpu_daemon}
|   ├─ proxy      : {cpu_proxy}
|   ├─ cargo      : {cpu_cargo}
|   └─ ftio       : {cpu_ftio}
├─ OMP threads    : {settings.omp_threads}
├─ max time       : {settings.max_time}
└─ job id         : {settings.job_id}

[bold green]ftio[/]{ftio_text}

[bold green]gekko[/]{gkfs_daemon_text}{gkfs_proxy_text}

[bold green] cargo[/]{cargo_text}

[bold green]app[/]
├─ app dir        : {settings.run_dir}
├─ app call       : {settings.app_call}
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

    with open(file, "a") as file:
        file.write(text)


def jit_print(s: str, new_line: bool = False) -> None:
    if new_line:
        console.print(f"\n[bold green]JIT[/][green] {s}[/]")
    else:
        console.print(f"[bold green]JIT[/][green] {s}[/]")


def create_hostfile(settings):
    jit_print(f"[cyan]>> Cleaning Hostfile: {settings.gkfs_hostfile}")

    try:
        if os.path.exists(settings.gkfs_hostfile):
            os.remove(settings.gkfs_hostfile)
            jit_print("[yellow]>> Hostfile removed[/]")
        else:
            jit_print("[green]>> No hostfile found to remove[/]")

    except Exception as e:
        jit_print(f"[bold red]Error removing hostfile:[/bold red] {e}", True)

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


def elapsed_time(settings: JitSettings, runtime: JitTime, name, elapsed):
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
        if "in" in name.lower():
            runtime.stage_in = elapsed
        elif "out" in name.lower():
            runtime.stage_out = elapsed
    elif "app" in name.lower():
        runtime.app = elapsed


def check(settings: JitSettings):
    if settings.dry_run or settings.exclude_daemon:
        return

    call = flaged_mpiexec_call(settings, f"ls -lahrt {settings.gkfs_mntdir}")
    try:

        files = subprocess.check_output(
            f"{call}",
            shell=True,
            text=True,
        )
        jit_print(f"[cyan]>> {call}: [/]\n{files}")
    except subprocess.CalledProcessError as e:
        jit_print(f"[red]>> Failed to list files in {settings.gkfs_mntdir}: {e}[/]")


def flaged_mpiexec_call(settings: JitSettings, call: str, procs: int = 1) -> str:
    additional_arguments = load_flags_mpiexec(settings)
    call, procs = clean_call(call,procs)
    if settings.cluster:
        call = mpiexec_call(settings, call, procs, additional_arguments)
    else:
        call = (
            f"mpiexec -np {procs} --oversubscribe "
            # f"-x LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')} "
            f"{additional_arguments} {call}"
        )

    return call


def load_flags_mpiexec(settings: JitSettings, ftio_metrics: bool = False) -> str:
    additional_arguments = ""
    if not settings.exclude_ftio and ftio_metrics:
        additional_arguments += f"-x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port} -x LIBGKFS_ENABLE_METRICS=on "
    if not settings.exclude_proxy:
        additional_arguments += f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
    if not settings.exclude_daemon:
        additional_arguments += (
            f"-x LIBGKFS_LOG=info,warnings,errors "
            f"-x LIBGKFS_LOG_OUTPUT={settings.gekko_client_log} "
            f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
            f"-x LD_PRELOAD={settings.gkfs_intercept} "
        )
    additional_arguments += get_env(settings,"mpi")
    return additional_arguments


def load_flags(settings: JitSettings, ftio_metrics: bool = False) -> str:
    additional_arguments = ""
    if not settings.exclude_ftio and ftio_metrics:
        additional_arguments += f" LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port}  LIBGKFS_ENABLE_METRICS=on "
    if not settings.exclude_proxy:
        additional_arguments += f" LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
    if not settings.exclude_daemon:
        additional_arguments += (
            f" LIBGKFS_LOG=info,warnings,errors "
            f" LIBGKFS_LOG_OUTPUT={settings.gekko_client_log} "
            f" LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
            f" LD_PRELOAD={settings.gkfs_intercept} "
        )
    return additional_arguments


def mpiexec_call(
    settings: JitSettings, command: str, procs: int = 1, additional_arguments=""
) -> str:
    call = (
        f" mpiexec -np {procs} --oversubscribe "
        f"--hostfile {settings.dir}/hostfile_mpi -map-by node "
        f"{additional_arguments} "
        f"{settings.task_set_0} {command}"
    )
    return call


def clean_call(call:str,procs:int):
    if "mpiexec" in call or "mpirun" in call:
        call = call.replace("mpiexec", "").replace("mpirun", "").strip()
        parts = call.split()
        if '-np' in parts:
            procs = int(parts[parts.index('-np') + 1]) 
            parts = [part for part in parts if part != '-np' and part != str(procs)]
            call = " ".join(parts)
    else:
        pass

    return call, procs


def update_hostfile_mpi(settings: JitSettings) -> None:
    # Command to get the list of hostnames for the job
    squeue_command = f"squeue -j {settings.job_id} -o '%N' | tail -n +2"
    scontrol_command = f"scontrol show hostname $({squeue_command})"

    # Execute the command and capture the hostnames
    hostnames = (
        subprocess.check_output(scontrol_command, shell=True).decode().splitlines()
    )

    # Write the hostnames to the file, excluding the Ftio node
    with open(f"{settings.dir}/hostfile_mpi", "w") as hostfile:
        for hostname in hostnames:
            if hostname.strip() != settings.ftio_node:
                hostfile.write(hostname + "\n")


def log_failed_jobs(settings: JitSettings, info: str) -> None:
    """Add failed job to a file

    Args:
        settings (JitSettings): Jit settings
        info (str): log text
    """
    parent = os.path.dirname(settings.log_dir)
    execution_path = os.path.join(parent, "execution.txt")
    try:
        jit_print(
            f"[yellow]>> Adding execution to list of failed jobs in {execution_path}.[/]"
        )
        with open(execution_path, "a") as file:
            file.write(f"- {info}\n")
    except:
        jit_print(f"[Red]>> Killing Job: {info}.\n Exiting script.[/]")


def set_env(settings: JitSettings):
    for _, key in enumerate(settings.env_var):
        jit_print(f"[green]>> Setting {key} to {settings.env_var[key]}[/]")
        os.environ[str(key)] = str(settings.env_var[key])
        jit_print(f"[cyan]>> {key} set to {os.getenv(str(key))}[/]")
        if os.getenv(str(key)) is None:
            jit_print(
                f"[red bold]>> {key} not set, do this manually:\nexport {key}={settings.env_var[key]}[/]"
            )


def get_env(settings: JitSettings,mode="srun") -> str:
    env = ""
    if "mpi" in mode:
        env = " ".join(f"-x {key}={value}" for key, value in settings.env_var.items())
    elif "srun": #srun
        env = ",".join(f"{key}={value}" for key, value in settings.env_var.items())
        env = "," + env
    else:
        pass
    return env




def save_bandwidth(settings: JitSettings):
    if not settings.exclude_ftio:
        try:
            command = f"cp {os.path.dirname(settings.log_dir)}/bandwidth.json {settings.log_dir}/bandwidth.json || true"
            _ = subprocess.run(
                command, shell=True, capture_output=True, text=True, check=True
            )
        except Exception as e:
            jit_print(f"[red] >> Error saving bandwidth:\n{e}")
