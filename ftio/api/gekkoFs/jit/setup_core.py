import os
import subprocess
from rich.console import Console
import time
from ftio.api.gekkoFs.jit.setup_check import check_setup
from ftio.api.gekkoFs.jit.setup_helper import (
    check,
    check_port,
    create_hostfile,
    elapsed_time,
    jit_print,
    relevant_files,
    reset_relevant_files,
    shut_down,
)
from ftio.api.gekkoFs.jit.execute_and_wait import (
    end_of_transfer,
    execute_block,
    execute_block_and_log,
    execute_background,
    execute_background_and_log,
    execute_background_and_wait_line,
    get_time,
    monitor_log_file,
    wait_for_file,
    wait_for_line,
)
from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.jittime import JitTime

console = Console()


#! Start gekko
#!#################
def start_gekko_demon(settings: JitSettings) -> None:

    if settings.exclude_demon:
        console.print(f"[bold yellow]####### Skipping Gkfs Demon [/][black][{get_time()}][/]")
    else:
        console.print(f"[bold green]####### Starting Gkfs Demon [/][black][{get_time()}][/]")

        # Create host file
        create_hostfile(settings)

        if settings.cluster:
            # Display Demon
            # call_0 = f"srun --jobid={settings.job_id} {settings.single_node_command} -N 1 --ntasks=1 mkdir -p {settings.gkfs_mntdir}"
            call_0 =(
                f"srun --jobid={settings.job_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                f"--ntasks={settings.app_nodes} --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap "
                f"--oversubscribe --mem=0 mkdir -p {settings.gkfs_mntdir}"
                    )
            if settings.exclude_proxy:
                # Demon call without proxy
                # call = (
                #     f"srun --jobid={settings.job_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                #     f"--ntasks={settings.app_nodes*settings.procs_demon} --cpus-per-task={settings.procs_demon} --ntasks-per-node={settings.procs_demon} --overcommit --overlap "
                #     f"--oversubscribe --mem=0 {settings.gkfs_demon} -r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                #     f"-H {settings.gkfs_hostfile} -c -l ib0 -P ofi+sockets"
                # )
                call = (
                    f"srun --jobid={settings.job_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                    f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs_demon} --ntasks-per-node=1 --overcommit --overlap "
                    f"--oversubscribe --mem=0 {settings.gkfs_demon} -r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                    f"-H {settings.gkfs_hostfile} -c -l ib0 -P ofi+sockets"
                )
            else:
                # Demon call with proxy
                call = (
                    f"srun --jobid={settings.job_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                    f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs_demon} --ntasks-per-node=1 --overcommit --overlap "
                    f"--oversubscribe --mem=0 {settings.gkfs_demon} -r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                    f"-H {settings.gkfs_hostfile} -c -l ib0 -P ofi+sockets -p ofi+verbs -L ib0"
                )

        else:
            call_0 = f"mkdir -p {settings.gkfs_mntdir}"

            # Gekko demon call
            call = (
                f"GKFS_DAEMON_LOG_LEVEL=info GKFS_DAEMON_LOG_PATH={settings.gekko_demon_log} {settings.gkfs_demon} -r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                f"-H {settings.gkfs_hostfile} -c -l lo -P ofi+tcp --proxy-listen lo --proxy-protocol ofi+tcp"
            )

        out = execute_block(call_0)
        jit_print(f"[cyan]>> Creating directory\n{out}[/]")

        jit_print("[cyan]>> Starting Demons[/]")
        
        if settings.debug:
            process = execute_background_and_log(settings, call, settings.gekko_demon_log, "demon",settings.gekko_demon_err)
            monitor_log_file(settings.gekko_demon_err,"Error Demon")
        else:
            process = execute_background_and_log(settings, call, settings.gekko_demon_log, "demon")
        
        wait_for_file(settings.gkfs_hostfile)
        console.print("\n")


#! Start Proxy
#!#######################
def start_gekko_proxy(settings: JitSettings) -> None:
    if settings.exclude_proxy:
        console.print(f"[bold yellow]####### Skipping Gkfs Proxy [/][black][{get_time()}][/]")
    else:
        console.print(f"[bold green]####### Starting Gkfs Proxy [/][black][{get_time()}][/]")

        if settings.cluster:
            # Proxy call for cluster
            call = (
                f"srun --jobid={settings.job_id} {settings.app_nodes_command} "
                f"--disable-status -N {settings.app_nodes} --ntasks={settings.app_nodes} "
                f"--cpus-per-task={settings.procs_proxy} --ntasks-per-node=1 --overcommit "
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

        if settings.debug:
            process = execute_background_and_log(settings, call, settings.gekko_proxy_log, "proxy", settings.gekko_proxy_err)
            monitor_log_file(settings.gekko_proxy_err,"Error Proxy")
        else:
            process = execute_background_and_log(settings, call, settings.gekko_proxy_log, "proxy")
        console.print("\n")


#! start Cargo
#!#################
def start_cargo(settings: JitSettings) -> None:
    if settings.exclude_cargo:
        console.print(f"[bold yellow]####### Skipping Cargo [/][black][{get_time()}][/]")
    else:
        console.print(f"[bold green]####### Starting Cargo [/][black][{get_time()}][/]")

        if settings.cluster:
            # Command for cluster
            # call = (
            #     f"srun --export=LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile},"
            #     f"LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')} --jobid={settings.job_id} "
            #     f"{settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
            #     f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs_cargo} --ntasks-per-node=1 "
            #     f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo} "
            #     f"--listen ofi+sockets://ib0:62000 -b 65536"
            # )
            # The above call just gives more resources to the same proc, but not more. Cargo need at least two
            call = (
                f"srun --export=LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile},LIBGKFS_LOG_OUTPUT={settings.gekko_client_log},"
                f"LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')} --jobid={settings.job_id} "
                f"{settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                f"--ntasks={settings.app_nodes*settings.procs_cargo} --cpus-per-task={settings.procs_cargo} --ntasks-per-node={settings.procs_cargo} "
                f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo} "
                f"--listen ofi+sockets://ib0:62000 -b 65536"
            )
        else:
            # Command for non-cluster
            call = (
                f"mpiexec -np {settings.procs_cargo} --oversubscribe -x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')} {settings.cargo} "
                f"--listen ofi+tcp://127.0.0.1:62000 -b 65536"
            )

        jit_print("[cyan]>> Starting Cargo[/]")

        if settings.debug:
            process = execute_background_and_log(settings, call, settings.cargo_log, "cargo", settings.cargo_err)
            monitor_log_file(settings.cargo_err,"Error Cargo")
        else:
            process = execute_background_and_log(settings, call, settings.cargo_log, "cargo")
        # wait for line to appear
        time.sleep(5)
        wait_for_line(settings.cargo_log, "Start up successful")
        console.print("\n")

#! start FTIO
#!################
def start_ftio(settings: JitSettings) -> None:
    if settings.exclude_ftio or settings.exclude_all:
        console.print(f"[bold yellow]####### Skipping FTIO [/][black][{get_time()}][/]")

        relevant_files(settings, True)

        if not settings.exclude_cargo:
            console.print(
                "[bold yellow]Executing the calls below used later for staging out[/]"
            )
            call_0 = (
                f"srun --jobid={settings.job_id} {settings.single_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_cli}/cargo_ftio "
                f"--server {settings.cargo_server} --run"
            )
            call_1 = (
                f"srun --jobid={settings.job_id} {settings.single_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_cli}/ccp "
                f"--server {settings.cargo_server} --input / --output {settings.stage_out_path} "
                f"--if gekkofs --of parallel"
            )
            _ = execute_block(call_0)
            _ = execute_block(call_1)
    else:
        console.print(f"[bold green]####### Starting FTIO [/][black][{get_time()}][/]")

        relevant_files(settings, True)

        if settings.cluster:
            # console.print(f"source {settings.ftio_activate}")
            jit_print(
                f"[cyan]>> FTIO started on node {settings.ftio_node}, remaining nodes for the application: {settings.app_nodes} each with {settings.procs_ftio} processes [/]"
            )
            jit_print(
                f"[cyan]>> FTIO is listening node is {settings.address_ftio}:{settings.port} [/]"
            )

            call = (
                f"srun --jobid={settings.job_id} {settings.ftio_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task={settings.procs_ftio} "
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

        if settings.debug:
            process = execute_background_and_log(settings, call, settings.ftio_log, "ftio", settings.ftio_err)
            monitor_log_file(settings.ftio_err,"Error Ftio")
        else:
            process = execute_background_and_log(settings, call, settings.ftio_log, "ftio")
        
        wait_for_line(settings.ftio_log, "FTIO is running on:", "Waiting for FTIO startup")
        time.sleep(5)
        console.print("\n")

#! Stage in
#!################
def stage_in(settings: JitSettings, runtime: JitTime) -> None:
    if settings.exclude_all:
        console.print(f"[bold yellow]####### Skipping Stage in [/][black][{get_time()}][/]")
    else:
        console.print(f"[bold green]####### Staging in [/][black][{get_time()}][/]")

        if settings.cluster:
            call = f"srun --jobid={settings.job_id} {settings.single_node_command} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 {settings.cargo_cli}/ccp --server {settings.cargo_server} --output / --input {settings.stage_in_path} --of gekkofs --if parallel"
        else:
            call = f"mpiexec -np 1 --oversubscribe {settings.cargo_cli}/ccp --server {settings.cargo_server} --output / --input {settings.stage_in_path} --of gekkofs --if parallel"

        start = time.time()

        execute_background_and_wait_line(
            call,
            settings.cargo_log,
            "retval: CARGO_SUCCESS, status: {state: completed",
        )
        # process = execute_background(call, cargo_log)
        # wait_for_line(cargo_log, "Start up successful")
        
        elapsed_time(settings, runtime, "Stage in", time.time() - start)
        check(settings)


#! Stage out
#!################
def stage_out(settings: JitSettings, runtime: JitTime) -> None:
    if settings.exclude_all:
        console.print(f"[bold yellow]####### Skipping  Stage out [/][black][{get_time()}][/]")
    else:
        console.print(f"[bold green]####### Staging out [/][black][{get_time()}][/]")
        
        reset_relevant_files(settings)       
        time.sleep(8)

        try:
            command_ls = f"LD_PRELOAD={settings.gkfs_intercept} LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} ls {settings.gkfs_mntdir}"
            files = subprocess.check_output(command_ls, shell=True).decode()
            console.print(f"[cyan]>> gekko_ls {settings.gkfs_mntdir}: \n{files}[/]")
        except Exception as e:
                console.print(f"[bold green]JIT[/][red] >> Error during test:\n{e}")
        # Reset relevant files
        if settings.cluster:
            call = (f"srun --jobid={settings.job_id} {settings.single_node_command} "
                    f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                    f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_cli}/cargo_ftio "
                    f"--server {settings.cargo_server} --run")
        else:
            call = (f"mpiexec -np 1 --oversubscribe {settings.cargo_cli}/cargo_ftio "
                    f"--server {settings.cargo_server} --run")

        
        # Measure and print elapsed time
        start = time.time()
        execute_background_and_wait_line(
            call,
            settings.cargo_log,
            "[info] Transfer finished for ["
        )
        end_of_transfer(settings, settings.cargo_log,call)
        elapsed_time(settings, runtime, "Stage out", time.time() - start)
        # Set ignored files to default again
        relevant_files(settings)
        time.sleep(5)


#! App call
#!################
def start_application(settings: JitSettings, runtime: JitTime):
    console.print(f"[green bold]####### Executing Application [/][black][{get_time()}][/]")
    # Placeholder for setup check
    check_setup(settings)
    if settings.cluster:
        # without FTIO
		#? [--stag in (si)--]               [--stag out (so)--]
		#?              [---APP---]
		# with FTIO
		#? [--stag in--]   [so]  [so] ... [so]
		#?              [---APP---]

        if settings.exclude_all:
            call = (
                f"{settings.precall} mpiexec -np {settings.procs_app} --oversubscribe "
                f"--hostfile ~/hostfile_mpi --map-by node {settings.app_call}"
            )
        elif settings.exclude_ftio:
            call = (
                f"{settings.precall} mpiexec -np {settings.procs_app} --oversubscribe "
                f"--hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=info,warnings,errors "
                f"-x LD_PRELOAD={settings.gkfs_intercept} "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                f"-x LIBGKFS_LOG_OUTPUT={settings.gekko_client_log} "
                f"{settings.app_call}"
            )
        else:
            call = (
                f"{settings.precall} mpiexec -np {settings.procs_app} --oversubscribe "
                f"--hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=info,warnings,errors "
                f"-x LIBGKFS_ENABLE_METRICS=on -x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port} "
                f"-x LD_PRELOAD={settings.gkfs_intercept} "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                f"-x LIBGKFS_LOG_OUTPUT={settings.gekko_client_log} "
                f"{settings.app_call}"
            )
    else:
        # Define the call for non-cluster environment
        if settings.exclude_all:
            call = f"{settings.precall} mpiexec -np {settings.procs_app} --oversubscribe {settings.app_call}"
        elif settings.exclude_ftio:
            call = (
                f"{settings.precall} mpiexec -np {settings.procs_app} --oversubscribe "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LIBGKFS_LOG=info,warnings,errors -x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                f"-x LD_PRELOAD={settings.gkfs_intercept} {settings.app_call}"
            )
        else:
            call = (
                f"{settings.precall} mpiexec -np {settings.procs_app} --oversubscribe "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LIBGKFS_LOG=none -x LIBGKFS_ENABLE_METRICS=on "
                f"-x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port} "
                f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                f"-x LD_PRELOAD={settings.gkfs_intercept} {settings.app_call}"
            )

    # elapsed = execute_block_and_log(call, settings.app_log_dir)   
    start = time.time()
    process = execute_background(call, settings.app_log, settings.app_err)
    monitor_log_file(settings.app_log,"")
    monitor_log_file(settings.app_err,"error")
    # monitor_log_file(settings.gekko_client_log,"Client")
    stdout, stderr = process.communicate()
    elapsed_time(settings, runtime, "App", time.time() - start)
    if process.returncode != 0:
        console.print(f"[red]Error executing command:{call}")
        console.print(f"[red] Error was:\n{stderr}")
    else:
        # console.print(stdout, style="bold green")
        pass

    if not settings.exclude_ftio:
        jit_print("[cyan]>> Shuting down FTIO as application finished")
        shut_down(settings, "FTIO", settings.ftio_pid)


#! Pre app call
#!################
def pre_call(settings: JitSettings) -> None:
    if settings.pre_app_call:
        console.print(f"[green bold]####### Pre-application Call [/][black][{get_time()}][/]")
        _ = execute_block_and_log(
            settings.pre_app_call, settings.app_log
        )


#! Post app call
#!################
def post_call(settings: JitSettings) -> None:
    if settings.post_app_call:
        console.print(f"[green bold]####### Post-application Call [/][black][{get_time()}][/]")
        _ = execute_block_and_log(
            settings.post_app_call, settings.app_log
        )




