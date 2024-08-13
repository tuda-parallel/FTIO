import os
import subprocess
from rich.console import Console
import time
from ftio.api.gekkoFs.jit.setup_helper import (
    check,
    check_port,
    check_setup,
    create_hostfile,
    elapsed_time,
    execute,
    execute_and_log,
    execute_and_wait_line,
    execute_background,
    jit_print,
    get_pid,
    monitor_log_file,
    relevant_files,
    reset_relevant_files,
    wait_for_file,
    wait_for_line,
)
from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.jittime import JitTime

console = Console()


#! Start gekko
#!#################
def start_geko_demon(settings: JitSettings) -> None:

    if settings.exclude_demon:
        console.print("\n[bold yellow]####### Skipping Gkfs Demon[/]")
    else:
        console.print("\n[bold green]####### Starting Gkfs Demon[/]")

        # Create host file
        create_hostfile(settings)

        if settings.cluster:
            # Display Demon
            call_0 = f"srun --jobid={settings.jit_id} {settings.single_node_command} -N 1 --ntasks=1 mkdir -p {settings.gkfs_mntdir}"
            settings.exclude_proxy = False

            if settings.exclude_proxy:
                # Demon call with proxy
                call = (
                    f"srun --jobid={settings.jit_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                    f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs} --ntasks-per-node=1 --overcommit --overlap "
                    f"--oversubscribe --mem=0 {settings.gkfs_demon} -r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                    f"-H {settings.gkfs_hostfile} -c -l ib0 -P ofi+sockets -p ofi+verbs -L ib0"
                )

            else:
                # Demon call without proxy
                call = (
                    f"srun --jobid={settings.jit_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                    f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs} --ntasks-per-node=1 --overcommit --overlap "
                    f"--oversubscribe --mem=0 {settings.gkfs_demon} -r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                    f"-H {settings.gkfs_hostfile} -c -l ib0 -P ofi+sockets"
                )

        else:
            call_0 = f"mkdir -p {settings.gkfs_mntdir}"

            # Geko Demon call
            call = (
                f"GKFS_DAEMON_LOG_LEVEL=info {settings.gkfs_demon} -r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                f"-H {settings.gkfs_hostfile} -c -l lo -P ofi+tcp --proxy-listen lo --proxy-protocol ofi+tcp"
            )

        jit_print("[cyan]>> Creating Directory[/]")
        _ = execute(call_0)

        jit_print("[cyan]>> Starting Demons[/]")
        geko_demon_log_dir = os.path.join(settings.log_dir, "geko_demon.log")
        process = execute_background(call, geko_demon_log_dir)
        get_pid(settings, "demon", process.pid)
        #demon is noisy
        # monitor_log_file(geko_demon_log_dir, "demon")

        # stdout, stderr = process.communicate()
        # if process.returncode != 0:
        #     console.print(f"[bold red]Error executing command:[/bold red] {call}", style="bold red")
        #     console.print(stderr, style="bold red")
        # else:
        #     console.print(stdout, style="bold green")

        wait_for_file(settings.gkfs_hostfile)
        console.print("\n")


#! Start Proxy
#!#######################
def start_geko_proxy(settings: JitSettings) -> None:
    if settings.exclude_proxy:
        console.print("\n[bold yellow]####### Skipping Gkfs Proxy[/]")
    else:
        console.print("\n[bold green]####### Starting Gkfs Proxy[/]")

        if settings.cluster:
            # Proxy call for cluster
            call = (
                f"srun --jobid={settings.jit_id} {settings.app_nodes_command} "
                f"--disable-status -N {settings.app_nodes} --ntasks={settings.app_nodes} "
                f"--cpus-per-task={settings.procs} --ntasks-per-node=1 --overcommit "
                f"--overlap --oversubscribe --mem=0 {settings.gkfs_proxy} "
                f"-H {settings.gkfs_hostfile} -p ofi+verbs -P {settings.gkfs_proxyfile}"
            )
        else:
            # Proxy call for non-cluster
            call = (
                f"{settings.gkfs_proxy} -H {settings.gkfs_hostfile} "
                f"-p ofi+tcp -P {settings.gkfs_proxyfile}"
            )
        jit_print("[cyan]>> Starting Proxy[/]")
        geko_proxy_log_dir = os.path.join(settings.log_dir, "geko_proxy.log")
        process = execute_background(call, geko_proxy_log_dir)
        get_pid(settings, "proxy", process.pid)
        monitor_log_file(geko_proxy_log_dir, "proxy")
        console.print("\n")


#! start Cargo
#!#################
def start_cargo(settings: JitSettings) -> None:
    if settings.exclude_cargo:
        console.print("\n[bold yellow]####### Skipping Cargo[/]")
    else:
        console.print("\n[bold green]####### Starting Cargo[/]")

        if settings.cluster:
            # Command for cluster
            call = (
                f"srun --export=LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile},"
                f"LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')} --jobid={settings.jit_id} "
                f"{settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs} --ntasks-per-node=1 "
                f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo} "
                f"--listen ofi+sockets://ib0:62000 -b 65536"
            )
        else:
            # Command for non-cluster
            call = (
                f"mpiexec -np 2 --oversubscribe -x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')} {settings.cargo} "
                f"--listen ofi+tcp://127.0.0.1:62000 -b 65536"
            )

        jit_print("[cyan]>> Starting Cargo[/]")
        cargo_log_dir = os.path.join(settings.log_dir, "cargo.log")
        process = execute_background(call, cargo_log_dir)
        get_pid(settings, "cargo", process.pid)
        monitor_log_file(cargo_log_dir, "cargo")

        # wait for line to appear
        time.sleep(5)
        wait_for_line(cargo_log_dir, "Start up successful")
        console.print("\n")

#! start FTIO
#!################
def start_ftio(settings: JitSettings) -> None:
    if settings.exclude_ftio or settings.exclude_all:
        console.print("\n[bold yellow]####### Skipping FTIO[/]")

        relevant_files(settings, True)

        if not settings.exclude_cargo:
            console.print(
                "[bold yellow]Executing the calls below used later for staging out[/]"
            )
            call_0 = (
                f"srun --jobid={settings.jit_id} {settings.single_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_cli}/cargo_ftio "
                f"--server {settings.cargo_server} --run"
            )
            call_1 = (
                f"srun --jobid={settings.jit_id} {settings.single_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_cli}/ccp "
                f"--server {settings.cargo_server} --input / --output {settings.stage_out_path} "
                f"--if gekkofs --of parallel"
            )
            execute(call_0)
            execute(call_1)
    else:
        console.print("\n[bold green]####### Starting FTIO[/]")

        relevant_files(settings, True)

        if settings.cluster:
            # console.print(f"source {settings.ftio_activate}")
            jit_print(
                f"[cyan] >> FTIO started on node {settings.ftio_node}, remaining nodes for the application: {settings.app_nodes} each with {settings.procs} processes [/]"
            )
            jit_print(
                f"[cyan] >> FTIO is listening node is {settings.address_ftio}:{settings.port} [/]"
            )

            call = (
                f"srun --jobid={settings.jit_id} {settings.ftio_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task={settings.procs} "
                f"--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 "
                f"predictor_jit --zmq_address {settings.address_ftio} --zmq_port {settings.port} "
                f"--cargo_cli {settings.cargo_cli} --cargo_server {settings.cargo_server} "
                f"--cargo_out {settings.stage_out_path}"
            )
        else:
            check_port(settings)
            call = (
                f"predictor_jit --zmq_address {settings.address_ftio} --zmq_port {settings.port} "
                f"--cargo_cli {settings.cargo_cli} --cargo_server {settings.cargo_server} "
                f"--cargo_out {settings.stage_out_path}"
            )

        jit_print("[cyan]>> Starting FTIO[/]")
        ftio_log_dir = os.path.join(settings.log_dir, "ftio.log")
        # process = execute(call)
        process = execute_background(call, ftio_log_dir)
        get_pid(settings, "ftio", process.pid)
        monitor_log_file(ftio_log_dir, "ftio")
        console.print("\n")

#! Stage in
#!################
def stage_in(settings: JitSettings, runtime: JitTime) -> None:
    if settings.exclude_all:
        console.print("\n[bold yellow]####### Skipping Stage in [/]")
    else:
        console.print("\n[bold green]####### Staging in [/]")

        if settings.cluster:
            command = f"srun --jobid={settings.jit_id} {settings.single_node_command} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 {settings.cargo_cli}/ccp --server {settings.cargo_server} --output / --input {settings.stage_in_path} --of gekkofs --if parallel"
        else:
            command = f"mpiexec -np 1 --oversubscribe {settings.cargo_cli}/ccp --server {settings.cargo_server} --output / --input {settings.stage_in_path} --of gekkofs --if parallel"

        start = time.time()
        execute_and_wait_line(
            command,
            os.path.join(settings.log_dir, "cargo.log"),
            "retval: CARGO_SUCCESS, status: {state: completed",
        )
        end = time.time()
        elapsed = end - start
        elapsed_time(settings, "Stage in", elapsed)
        runtime.stage_out = elapsed
        check(settings)


#! Stage out
#!################
def stage_out(settings: JitSettings, runtime: JitTime):
    if settings.exclude_all == 'true':
        console.print("\n[yellow]####### Skipping Stage out[/]")
    else:
        console.print("\n[green]####### Staging out[/]")


        command_ls = f"LD_PRELOAD={settings.gkfs_intercept} LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} ls {settings.gkfs_mntdir}"
        files = subprocess.check_output(command_ls, shell=True).decode()
        console.print(f"[cyan]>> geko_ls {settings.gkfs_mntdir}: \n{files}[/]")

        # Reset relevant files
        reset_relevant_files(settings)

        # Define the stage out command based on the cluster setting
        if settings.cluster == 'true':
            call = (f"srun --jobid={settings.jit_id} {settings.single_node_command} "
                    f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                    f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_cli}/cargo_ftio "
                    f"--server {settings.cargo_server} --run")
        else:
            call = (f"mpiexec -np 1 --oversubscribe {settings.cargo_cli}/cargo_ftio "
                    f"--server {settings.cargo_server} --run")

        # Measure and print elapsed time
        start_time = time.time()
        execute_and_wait_line(
            call,
            os.path.join(settings.log_dir, "cargo.log"),
            "Transfer finished for"
        )
        elapsed = time.time()

        elapsed_time(settings, "Stage out", elapsed)
        runtime.stage_out = elapsed
        # Set ignored files to default again
        relevant_files(settings)


#! App call
#!################
def start_application(settings: JitSettings, runtime: JitTime):
    console.print("\n[green]####### Executing Application[/]")
    # Placeholder for setup check
    check_setup(settings)
    if settings.cluster == True:
        # without FTIO
		#? [--stag in (si)--]               [--stag out (so)--]
		#?              [---APP---]
		# with FTIO
		#? [--stag in--]   [so]  [so] ... [so]
		#?              [---APP---]

        if settings.exclude_all == True:
            call = (
                f"{settings.precall} mpiexec -np {settings.procs} --oversubscribe "
                f"--hostfile ~/hostfile_mpi --map-by node {settings.app_call}"
            )
        elif settings.exclude_ftio == True:
            call = (
                f"{settings.precall} mpiexec -np {settings.procs} --oversubscribe "
                f"--hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=errors "
                f"-x LD_PRELOAD={settings.gkfs_intercept} "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                f"{settings.app_call}"
            )
        else:
            call = (
                f"{settings.precall} mpiexec -np {settings.procs} --oversubscribe "
                f"--hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=errors "
                f"-x LIBGKFS_ENABLE_METRICS=on -x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port} "
                f"-x LD_PRELOAD={settings.gkfs_intercept} "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                f"{settings.app_call}"
            )
    else:
        # Define the call for non-cluster environment
        if settings.exclude_all == True:
            call = f"{settings.precall} mpiexec -np {settings.procs} --oversubscribe {settings.app_call}"
        elif settings.exclude_ftio == True:
            call = (
                f"{settings.precall} mpiexec -np {settings.procs} --oversubscribe "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LIBGKFS_LOG=none -x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                f"-x LD_PRELOAD={settings.gkfs_intercept} {settings.app_call}"
            )
        else:
            call = (
                f"{settings.precall} mpiexec -np {settings.procs} --oversubscribe "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LIBGKFS_LOG=none -x LIBGKFS_ENABLE_METRICS=on "
                f"-x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port} "
                f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                f"-x LD_PRELOAD={settings.gkfs_intercept} {settings.app_call}"
            )

    # elapsed = execute_and_log(call, os.path.join(settings.log_dir, "app.log"))   

    app_log_dir = os.path.join(settings.log_dir, "geko_demon.log")
    start = time.time()
    process = execute_background(call, app_log_dir)
    monitor_log_file(app_log_dir)
    stdout, stderr = process.communicate()
    elapsed = time.time() -start

    stdout, stderr = process.communicate()
    if process.returncode != 0:
        console.print(f"[bold red]Error executing command:[/bold red] {call}", style="bold red")
        console.print(stderr, style="bold red")
    else:
        # console.print(stdout, style="bold green")
        pass
    
    elapsed_time(settings, "App", elapsed)
    runtime.app = elapsed
    settings.finish = True


#! Pre app call
#!################
def pre_call(settings: JitSettings) -> None:
    if settings.pre_app_call:
        console.print("\n[green]####### Pre-application Call[/]")
        _ = execute_and_log(
            settings.pre_app_call, os.path.join(settings.log_dir, "app.log")
        )


#! Post app call
#!################
def post_call(settings: JitSettings) -> None:
    if settings.post_app_call:
        console.print("\n[green]####### post-application Call[/]")
        _ = execute_and_log(
            settings.post_app_call, os.path.join(settings.log_dir, "app.log")
        )


