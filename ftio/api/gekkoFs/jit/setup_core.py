import os
import time

# import multiprocessing
import subprocess
from rich.console import Console

from ftio.api.gekkoFs.jit.setup_check import check_setup
from ftio.api.gekkoFs.jit.setup_helper import (
    check,
    check_port,
    elapsed_time,
    flaged_call,
    get_env,
    get_executable_realpath,
    handle_sigint,
    jit_print,
    mpiexec_call,
    relevant_files,
    reset_relevant_files,
    shut_down,
)
from ftio.api.gekkoFs.jit.execute_and_wait import (
    end_of_transfer_online,
    execute_block,
    execute_background,
    execute_background_and_log,
    execute_background_and_wait_line,
    execute_block_and_monitor,
    get_time,
    monitor_log_file,
    wait_for_file,
    wait_for_line,
)
from ftio.api.gekkoFs.jit.setup_init import init_gekko
from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.jittime import JitTime

console = Console()


#! Start gekko
#!#################
def start_gekko_daemon(settings: JitSettings) -> None:

    if settings.exclude_daemon:
        console.print(
            f"[bold yellow]####### Skipping Gkfs Demon [/][black][{get_time()}][/]"
        )
    else:
        console.print(
            f"[bold green]####### Starting Gkfs Demon [/][black][{get_time()}][/]"
        )
        # Create host file and dirs for geko
        init_gekko(settings)
        debug_flag = ""
        if settings.debug:
            debug_flag = "--export=ALL,GKFS_DAEMON_LOG_LEVEL=trace"

        if settings.cluster:
            if settings.use_mpirun:
                # mpiexec
                call = (
                    f"{settings.gkfs_daemon} "
                    f"-r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                    f"-H {settings.gkfs_hostfile}  -c --clean-rootdir -l ib0 -P {settings.gkfs_daemon_protocol}"
                )
                call = mpiexec_call(settings, call, settings.app_nodes)
            else:
                call = (
                    f"srun {debug_flag} --jobid={settings.job_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                    #   f"--ntasks={settings.app_nodes*settings.procs_daemon} --cpus-per-task={settings.procs_daemon} --ntasks-per-node={settings.procs_daemon} --overcommit --overlap "
                    f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs_daemon} --ntasks-per-node=1 --overcommit --overlap "
                    f"--oversubscribe --mem=0 {settings.task_set_0} {settings.gkfs_daemon} -r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                    f"-H {settings.gkfs_hostfile}  -c --clean-rootdir -l ib0 -P {settings.gkfs_daemon_protocol}"
                )
            if not settings.exclude_proxy:
                # Demon call with proxy
                call += " -p ofi+verbs -L ib0"
        else:  # no cluster mode
            call = (
                f"GKFS_DAEMON_LOG_LEVEL=info GKFS_DAEMON_LOG_PATH={settings.gekko_daemon_log} {settings.gkfs_daemon} -r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                f"-H {settings.gkfs_hostfile}  -c --clean-rootdir -l lo -P ofi+tcp"
            )
            if not settings.exclude_proxy:
                # Demon call with proxy
                call += " --proxy-listen lo --proxy-protocol ofi+tcp"

        jit_print("[cyan]>> Starting Demons[/]", True)
        # p = multiprocessing.Process(target=execute_background, args= (call, settings.gekko_daemon_log, settings.gekko_daemon_err, settings.dry_run))
        # p.start()
        # if settings.verbose:
        #     _ = monitor_log_file(settings.gekko_daemon_err,"Error Demon")
        #     _ = monitor_log_file(settings.gekko_daemon_log,"Demon")
        _ = execute_background_and_log(
            settings,
            call,
            settings.gekko_daemon_log,
            "daemon",
            settings.gekko_daemon_err,
        )
        if settings.verbose:
            _ = monitor_log_file(settings.gekko_daemon_err, "Error Demon")

        wait_for_file(settings.gkfs_hostfile, dry_run=settings.dry_run)
        console.print("\n")


#! Start Proxy
#!#######################
def start_gekko_proxy(settings: JitSettings) -> None:
    if settings.exclude_proxy:
        console.print(
            f"[bold yellow]####### Skipping Gkfs Proxy [/][black][{get_time()}][/]"
        )
    else:
        console.print(
            f"[bold green]####### Starting Gkfs Proxy [/][black][{get_time()}][/]"
        )

        if settings.cluster:
            # Proxy call for cluster
            call = (
                f"srun --jobid={settings.job_id} {settings.app_nodes_command} "
                f"--disable-status -N {settings.app_nodes} --ntasks={settings.app_nodes} "
                f"--cpus-per-task={settings.procs_proxy} --ntasks-per-node=1 --overcommit "
                f"--overlap --oversubscribe --mem=0 {settings.task_set_1} {settings.gkfs_proxy} "
                f"-H {settings.gkfs_hostfile} -p ofi+verbs -P {settings.gkfs_proxyfile}"
            )
        else:
            # Proxy call for non-cluster
            call = (
                f"{settings.gkfs_proxy} -H {settings.gkfs_hostfile} "
                f"-p ofi+tcp -P {settings.gkfs_proxyfile}"
            )
        jit_print("[cyan]>> Starting Proxy[/]")

        # p = multiprocessing.Process(target=execute_background, args= (call, settings.gekko_proxy_log, settings.gekko_proxy_err, settings.dry_run))
        # p.start()
        # if settings.verbose:
        #     _ = monitor_log_file(settings.gekko_proxy_log,"Proxy")
        #     _ = monitor_log_file(settings.gekko_proxy_err,"Error Proxy")

        _ = execute_background_and_log(
            settings, call, settings.gekko_proxy_log, "proxy", settings.gekko_proxy_err
        )
        if settings.verbose:
            _ = monitor_log_file(settings.gekko_proxy_err, "Error Proxy")

        console.print("\n")


#! start Cargo
#!#################
def start_cargo(settings: JitSettings) -> None:
    if settings.exclude_cargo:
        console.print(
            f"[bold yellow]####### Skipping Cargo [/][black][{get_time()}][/]"
        )
    else:
        console.print(f"[bold green]####### Starting Cargo [/][black][{get_time()}][/]")

        if settings.cluster:
            call = (
                f"{settings.cargo} "
                f"--listen {settings.gkfs_daemon_protocol}://ib0:62000 -b 65536"
            )
            call = flaged_call(settings, call, settings.app_nodes,  settings.procs_cargo)
        else:
            # Command for non-cluster
            call = f"{settings.cargo} --listen ofi+tcp://127.0.0.1:62000 -b 65536"
            call = flaged_call(settings, call, 1, settings.procs_cargo)

        jit_print("[cyan]>> Starting Cargo[/]")

        # p_cargo = multiprocessing.Process(target=execute_background,args=(call, settings.cargo_log, settings.cargo_err, settings.dry_run))
        # p_cargo.start()
        # if settings.verbose:
        #     _ = monitor_log_file(settings.cargo_log,"Cargo")
        #     _ = monitor_log_file(settings.cargo_err,"Error Cargo")

        process = execute_background_and_log(
            settings, call, settings.cargo_log, "cargo", settings.cargo_err
        )
        if settings.verbose:
            _ = monitor_log_file(settings.cargo_err, "Error Cargo")
        # wait for line to appear
        time.sleep(2)
        flag = wait_for_line(
            settings.cargo_log, "Start up successful", dry_run=settings.dry_run
        )
        if not flag:
            handle_sigint(settings)
        time.sleep(4)
        console.print("\n")


#! start FTIO
#!################
def start_ftio(settings: JitSettings) -> None:
    if settings.exclude_ftio or settings.exclude_all:
        console.print(f"[bold yellow]####### Skipping FTIO [/][black][{get_time()}][/]")

        relevant_files(settings)

        if settings.cluster and not settings.exclude_cargo:
            console.print(
                "[bold yellow]Executing the calls below used later for staging out[/]"
            )
            call_0 = (
                f"srun --jobid={settings.job_id} {settings.single_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_bin}/cargo_ftio "
                f"--server {settings.cargo_server} --run"
            )
            call_1 = (
                f"srun --jobid={settings.job_id} {settings.single_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_bin}/ccp "
                f"--server {settings.cargo_server} --input / --output {settings.stage_out_path} "
                f"--if gekkofs --of {settings.cargo_mode}"
            )

            _ = execute_block(call_0, dry_run=settings.dry_run)
            _ = execute_block(call_1, dry_run=settings.dry_run)
    else:
        console.print(f"[bold green]####### Starting FTIO [/][black][{get_time()}][/]")

        relevant_files(settings)

        if settings.cluster:
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
                    f"{settings.ftio_bin_location}/predictor_jit --zmq_address {settings.address_ftio} --zmq_port {settings.port} "
            )
            if settings.exclude_cargo:
                call +=(
                    f" --stage_out_path {settings.stage_out_path} --stage_in_path {settings.stage_in_path} --regex {settings.regex_match}"
                )
            else:
                call +=(
                    f"--cargo --cargo_bin {settings.cargo_bin} "
                    f"--cargo_server {settings.cargo_server} --stage_out_path {settings.stage_out_path}"
                )
        else:
            check_port(settings)
            call = (
                f"{settings.ftio_bin_location}/predictor_jit --zmq_address {settings.address_ftio} --zmq_port {settings.port} "
                f"--cargo --cargo_bin {settings.cargo_bin} --cargo_server {settings.cargo_server} "
                f"--stage_out_path {settings.stage_out_path}"
            )

        jit_print("[cyan]>> Starting FTIO[/]")

        process = execute_background_and_log(
            settings, call, settings.ftio_log, "ftio", settings.ftio_err
        )
        if settings.verbose:
            _ = monitor_log_file(settings.ftio_err, "Error Ftio")

        # p_ftio = multiprocessing.Process(target=execute_background,args=(call, settings.ftio_log, settings.ftio_err, settings.dry_run))
        # p_ftio.start()

        # if settings.verbose:
        #     _ = monitor_log_file(settings.ftio_log,"Ftio")
        #     _ = monitor_log_file(settings.ftio_err,"Error Ftio")

        if not settings.exclude_cargo:
            _ = wait_for_line(
                settings.ftio_log,
                "FTIO is running on:",
                "Waiting for FTIO startup",
                dry_run=settings.dry_run,
            )
        time.sleep(8)
        console.print("\n")


#! Stage in
#!################
def stage_in(settings: JitSettings, runtime: JitTime) -> None:
    if settings.exclude_all:
        console.print(
            f"[bold yellow]####### Skipping Stage in [/][black][{get_time()}][/]"
        )
    else:
        console.print(f"[bold green]####### Staging in [/][black][{get_time()}][/]")

        # remove locks
        jit_print("[cyan]>> Cleaning locks")
        if settings.stage_in_path:
            execute_block(
                f"cd {settings.stage_in_path} && rm -f  $(find .  | grep .lock)"
            )

        jit_print(f"[cyan]>> Staging in to {settings.stage_in_path}", True)

        if settings.exclude_cargo:
            # call = f"LD_PRELOAD={settings.gkfs_intercept} LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} cp -r {settings.stage_in_path}/* {settings.gkfs_mntdir}"
            call = flaged_call(
                settings, f"cp -r {settings.stage_in_path}/* {settings.gkfs_mntdir}"
            )
            start = time.time()
            _ = execute_block(call, dry_run=settings.dry_run)
        else:
            if settings.cluster:
                call = f"srun --jobid={settings.job_id} {settings.single_node_command} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 {settings.cargo_bin}/ccp --server {settings.cargo_server} --output / --input {settings.stage_in_path} --of gekkofs --if {settings.cargo_mode}"
            else:
                call = f"mpiexec -np 1 --oversubscribe {settings.cargo_bin}/ccp --server {settings.cargo_server} --output / --input {settings.stage_in_path} --of gekkofs --if {settings.cargo_mode}"

            start = time.time()

            execute_background_and_wait_line(
                call,
                settings.cargo_log,
                "retval: CARGO_SUCCESS, status: {state: completed",
                settings.dry_run,
            )

        elapsed_time(settings, runtime, "Stage in", time.time() - start)
        check(settings)


#! Stage out
#!################
def stage_out(settings: JitSettings, runtime: JitTime) -> None:
    if settings.exclude_all:
        console.print(
            f"[bold yellow]####### Skipping  Stage out [/][black][{get_time()}][/]"
        )
    else:
        if settings.exclude_cargo:
            # additional_arguments = load_flags(settings)
            # call = f"{additional_arguments} cp -r  {settings.gkfs_mntdir}/* {settings.stage_out_path} "
            call = flaged_call(
                settings,
                f"cp -r  {settings.gkfs_mntdir} {settings.stage_out_path} || echo 'nothing to stage in'",
            )
            start = time.time()
            _ = execute_block(call, dry_run=settings.dry_run)
            elapsed_time(settings, runtime, "Stage in", time.time() - start)
        else:
            console.print(
                f"[bold green]####### Staging out [/][black][{get_time()}][/]"
            )
            reset_relevant_files(settings)
            # time.sleep(8)

            if not settings.dry_run:
                try:
                    call = flaged_call(
                        settings, f"ls -R {settings.gkfs_mntdir}"
                    )
                    files = subprocess.check_output(call, shell=True).decode()
                    console.print(
                        f"[cyan]>> gekko_ls {settings.gkfs_mntdir}: \n{files}[/]"
                    )
                except Exception as e:
                    jit_print(f"[red] >> Error during test:\n{e}")

            # Reset relevant files
            if settings.cluster:
                call = (
                    f"srun --jobid={settings.job_id} {settings.single_node_command} "
                    f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                    f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_bin}/cargo_ftio "
                    f"--server {settings.cargo_server} --run"
                )
            else:
                call = (
                    f"mpiexec -np 1 --oversubscribe {settings.cargo_bin}/cargo_ftio "
                    f"--server {settings.cargo_server} --run"
                )

            # Measure and print elapsed time
            start = time.time()
            execute_background_and_wait_line(
                call,
                settings.cargo_log,
                # "[info] Transfer finished for [",
                "ftio_int RPC was successful!",
                settings.dry_run,
            )
            # end_of_transfer(settings, settings.cargo_log,call)
            end_of_transfer_online(settings, settings.cargo_log, call)
            elapsed_time(settings, runtime, "Stage out", time.time() - start)
            # Set ignored files to default again
            relevant_files(settings)
            time.sleep(5)


#! App call
#!################
def start_application(settings: JitSettings, runtime: JitTime):
    name = (
        settings.app_call.split("/", 1)[1]
        if "/" in settings.app_call
        else settings.app_call
    )
    console.print(
        f"[green bold]####### Executing Application {name} [/][black][{get_time()}][/]"
    )
    # set up dir
    original_dir = settings.dir
    jit_print(f">> Current directory {original_dir}")
    if not settings.dry_run:
        check_setup(settings)
        # pass

    if settings.cluster:
        additional_arguments = ""
        if settings.use_mpirun:
            if not settings.exclude_ftio:
                additional_arguments += f"-x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port} -x LIBGKFS_ENABLE_METRICS=on "
            if not settings.exclude_proxy:
                additional_arguments += (
                    f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                )
            if not settings.exclude_daemon:
                additional_arguments += (
                    f"-x LIBGKFS_LOG=info,warnings,errors "
                    f"-x LIBGKFS_LOG_OUTPUT={settings.gekko_client_log} "
                    f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                    f"-x LD_PRELOAD={settings.gkfs_intercept} "
                )

            call = (
                # f" cd {settings.run_dir} && "
                # f"strace -f -e trace=read,write,open,close,stat,fstat,lseek,access -o /gpfs/fs1/home/tarrafah/strace_n{settings.app_nodes}_p{settings.procs_app}.txt mpiexec -np {settings.app_nodes*settings.procs_app} --oversubscribe "
                # f" cd {settings.run_dir} && time -p mpiexec --mca errhandler ftmpi --mca mpi_abort_print_stack 1  -np {settings.app_nodes*settings.procs_app} --oversubscribe "
                f" cd {settings.run_dir} && time -p mpiexec -np {settings.app_nodes*settings.procs_app} --oversubscribe "
                f"--hostfile {settings.dir}/hostfile_mpi --map-by node "
                f"{additional_arguments} "
                f"{settings.task_set_1} {settings.app_call} {settings.app_flags}"
            )
        else:
            if not settings.exclude_ftio:
                additional_arguments += f"LIBGKFS_ENABLE_METRICS=on,LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port},"
            if not settings.exclude_proxy:
                additional_arguments += (
                    f"LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile},"
                )
            if not settings.exclude_daemon:
                additional_arguments += (
                    f"LIBGKFS_LOG=info,warnings,errors,"
                    f"LIBGKFS_LOG_OUTPUT={settings.gekko_client_log},"
                    f"LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile},"
                    f"LD_PRELOAD={settings.gkfs_intercept},"
                )

            app_call = get_executable_realpath(settings.app_call,settings.run_dir)
            call = (
                f" cd {settings.run_dir} && time -p srun "
                f"--export=ALL,{additional_arguments}LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')} "
                f"--jobid={settings.job_id} {settings.app_nodes_command} --disable-status "
                f"-N {settings.app_nodes} --ntasks={settings.app_nodes*settings.procs_app} "
                f"--cpus-per-task={settings.procs_app} --ntasks-per-node={settings.procs_app} "
                f"--overcommit --overlap --oversubscribe --mem=0 "
                f"{settings.task_set_1} {app_call} {settings.app_flags}"
            )
    else:
        # Define the call for non-cluster environment
        if settings.run_dir:
            os.chdir(settings.run_dir)
            jit_print(f">> Changing directory to  {os.getcwd()}")

        if settings.exclude_all:
            call = f" time mpiexec -np {settings.procs_app} --oversubscribe {settings.app_call} {settings.app_flags}"
        elif settings.exclude_ftio:
            call = (
                f" time mpiexec -np {settings.procs_app} --oversubscribe "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LIBGKFS_LOG=info,warnings,errors -x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                f"-x LD_PRELOAD={settings.gkfs_intercept} {settings.app_call} {settings.app_flags}"
            )
        else:
            call = (
                f" time mpiexec -np {settings.procs_app} --oversubscribe "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LIBGKFS_LOG=none -x LIBGKFS_ENABLE_METRICS=on "
                f"-x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port} "
                f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                f"-x LD_PRELOAD={settings.gkfs_intercept} {settings.app_call} {settings.app_flags}"
            )

    # elapsed = execute_block_and_log(call, settings.app_log_dir)
    check(settings)
    start = time.time()
    # p_app = multiprocessing.Process(target=execute_background_and_log_in_process, args=(call, settings.app_log,"", settings.app_err, settings.dry_run))
    # p_app.start()
    # p_app.join()

    process = execute_background(
        call, settings.app_log, settings.app_err, settings.dry_run
    )
    if settings.verbose:
        _ = monitor_log_file(settings.app_log, "")
        _ = monitor_log_file(settings.app_err, f"{name} error")
    _, stderr = process.communicate()

    # get the real time
    # The timing result will be in stderr because 'time' outputs to stderr by default

    # Extract the 'real' time from the output
    real_time = time.time() - start
    try:
        with open(settings.app_err, "r") as file:
            for line in file:
                if line.startswith("real"):
                    real_time = min(float(line.split()[1]), real_time)
                    break
    except Exception as e:
        jit_print(f">>[red] Could not extract real time due to \n {e}[/]\n")

    elapsed_time(settings, runtime, "App", real_time)

    if process.returncode != 0:
        console.print(f"[red]Error executing command:{call}")
        console.print(f"[red] Error was:\n{stderr}")
    else:
        pass

    if not settings.exclude_ftio:
        jit_print("[cyan]>> Shuting down FTIO as application finished")
        shut_down(settings, "FTIO", settings.ftio_pid)

    os.chdir(original_dir)
    jit_print(f">> Changing directory to {os.getcwd()}")


#! Pre app call
#!################
def pre_call(settings: JitSettings) -> None:
    if settings.pre_app_call:
        console.print(
            f"[green bold]####### Pre-application Call [/][black][{get_time()}][/]"
        )
        # additional_arguments = load_flags(settings)
        if isinstance(settings.pre_app_call, str):
            call = settings.pre_app_call
            if any(x in call for x in ["mpiex", "mpirun"]):
                call = flaged_call(settings, call)
            execute_block_and_monitor(
                settings.verbose,
                call,
                settings.app_log,
                settings.app_err,
                settings.dry_run,
            )
        elif isinstance(settings.pre_app_call, list):
            for call in settings.pre_app_call:
                if any(x in call for x in ["mpiex", "mpirun"]):
                    call = flaged_call(settings, call)
                execute_block_and_monitor(
                    settings.verbose,
                    call,
                    settings.app_log,
                    settings.app_err,
                    settings.dry_run,
                )
        # _ = execute_block_and_log(
        #     settings.pre_app_call, settings.app_log
        # )


#! Post app call
#!################
def post_call(settings: JitSettings) -> None:
    if settings.post_app_call:
        console.print(
            f"[green bold]####### Post-application Call [/][black][{get_time()}][/]"
        )
        additional_arguments = ""  # load_flags(settings)
        if isinstance(settings.post_app_call, str):
            call = f"{additional_arguments} {settings.post_app_call}"
            execute_block_and_monitor(
                settings.verbose,
                call,
                settings.app_log,
                settings.app_err,
                settings.dry_run,
            )
        elif isinstance(settings.post_app_call, list):
            call = ""
            for s in settings.post_app_call:
                call = f"{additional_arguments} {s}"
                execute_block_and_monitor(
                    settings.verbose,
                    call,
                    settings.app_log,
                    settings.app_err,
                    settings.dry_run,
                )
