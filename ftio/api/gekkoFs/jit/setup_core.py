"""
This file provides functions to start and manage various components of the GLASS approach,
including the Gekko daemon, proxy, cargo, and FTIO. It also includes functions for staging
data in and out, and executing pre- and post-application calls.

Author: Ahmad Tarraf
Copyright (c) 2025 TU Darmstadt, Germany
Date: Aug 2024

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import os

# import multiprocessing
import subprocess
import time

from ftio.api.gekkoFs.jit.execute_and_wait import (
    end_of_transfer_online,
    execute_background,
    execute_background_and_log,
    execute_background_and_wait_line,
    execute_block,
    execute_block_and_monitor,
    get_time,
    monitor_log_file,
    wait_for_file,
    wait_for_line,
)
from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.jittime import JitTime
from ftio.api.gekkoFs.jit.setup_check import check_setup
from ftio.api.gekkoFs.jit.setup_helper import (
    adjust_regex,
    check,
    check_port,
    elapsed_time,
    exit_routine,
    extract_accurate_time,
    flaged_call,
    get_env,
    get_executable_realpath,
    handle_sigint,
    jit_print,
    mpiexec_call,
    relevant_files,
    shut_down,
)
from ftio.api.gekkoFs.jit.setup_init import init_gekko
from ftio.api.gekkoFs.posix_control import jit_move


#! Start gekko
#!###############################
def start_gekko_daemon(settings: JitSettings) -> None:
    """Starts the Gekko daemon.

    Args:
        settings (JitSettings): jit settings
    """
    if settings.exclude_daemon:
        jit_print(
            f"[bold yellow]############## Skipping Gkfs Demon [/][black][{get_time()}][/]"
        )
    else:
        jit_print(
            f"[bold green]############## Starting Gkfs Demon [/][black][{get_time()}][/]"
        )
        # Create host file and dirs for geko
        init_gekko(settings)

        if settings.use_mpirun:
            debug_flag = f"-x GKFS_DAEMON_LOG_LEVEL=err -x GKFS_DAEMON_LOG_PATH={settings.gkfs_daemon_log}_intern"
            # if settings.debug_lvl > 0:
            # debug_flag = debug_flag.replace("=err", "=trace")
        else:
            debug_flag = f"--export=ALL,GKFS_DAEMON_LOG_LEVEL=err,GKFS_DAEMON_LOG_PATH={settings.gkfs_daemon_log}_intern"
            if settings.debug_lvl > 0:
                debug_flag = debug_flag.replace("=err", "=trace")

        if settings.cluster:
            if settings.use_mpirun:
                # mpiexec
                call = (
                    f" {settings.gkfs_daemon} "
                    f"-r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                    f"-H {settings.gkfs_hostfile}  -c --clean-rootdir -l ib0 -P {settings.gkfs_daemon_protocol}"
                )
                call = mpiexec_call(
                    settings,
                    call,
                    settings.app_nodes,
                    additional_arguments=debug_flag,
                )
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
            if settings.debug_lvl > 0:
                debug_flag = "GKFS_DAEMON_LOG_LEVEL=trace"
            else:
                # debug_flag = "GKFS_DAEMON_LOG_LEVEL=debug"
                # debug_flag = "GKFS_DAEMON_LOG_LEVEL=trace"
                debug_flag = "GKFS_DAEMON_LOG_LEVEL=err"
            call = (
                f"{debug_flag} LIBGKFS_LOG=all  GKFS_DAEMON_LOG_PATH={settings.gkfs_daemon_log}_intern {settings.gkfs_daemon} -r {settings.gkfs_rootdir} -m {settings.gkfs_mntdir} "
                f"-H {settings.gkfs_hostfile}  -c --clean-rootdir -l lo -P {settings.gkfs_daemon_protocol}"
            )
            if not settings.exclude_proxy:
                # Demon call with proxy
                call += (
                    " --proxy-listen lo --proxy-protocol {settings.gkfs_daemon_protocol}"
                )

        jit_print("[cyan]Starting Demons[/]", True)
        # p = multiprocessing.Process(target=execute_background, args= (call, settings.gkfs_daemon_log, settings.gkfs_daemon_err, settings.dry_run))
        # p.start()
        # if settings.verbose:
        #     _ = monitor_log_file(settings.gkfs_daemon_err,"Error Demon")
        #     _ = monitor_log_file(settings.gkfs_daemon_log,"Demon")
        _ = execute_background_and_log(
            settings,
            call,
            settings.gkfs_daemon_log,
            "daemon",
            settings.gkfs_daemon_err,
        )
        if settings.verbose_error:
            _ = monitor_log_file(settings.gkfs_daemon_err, "Error Demon")

        wait_for_file(settings.gkfs_hostfile, dry_run=settings.dry_run)

    if not settings.exclude_daemon:
        jit_print(f"[green]############## Gkfs init finished ##############\n\n\n\n ")


#! Start Proxy
#!############################################
def start_gekko_proxy(settings: JitSettings) -> None:
    """Starts the Gekko proxy.

    Args:
        settings (JitSettings): jit settings
    """
    if settings.exclude_proxy:
        jit_print(
            f"[bold yellow]############## Skipping Gkfs Proxy [/][black][{get_time()}][/]"
        )
    else:
        jit_print(
            f"[bold green]############## Starting Gkfs Proxy [/][black][{get_time()}][/]"
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
                f"-p {settings.gkfs_daemon_protocol} -P {settings.gkfs_proxyfile}"
            )
        jit_print("[cyan]Starting Proxy[/]")

        # p = multiprocessing.Process(target=execute_background, args= (call, settings.gkfs_proxy_log, settings.gkfs_proxy_err, settings.dry_run))
        # p.start()
        # if settings.verbose:
        #     _ = monitor_log_file(settings.gkfs_proxy_log,"Proxy")
        # if settings.verbose_error:
        #     _ = monitor_log_file(settings.gkfs_proxy_err,"Error Proxy")

        _ = execute_background_and_log(
            settings,
            call,
            settings.gkfs_proxy_log,
            "proxy",
            settings.gkfs_proxy_err,
        )
        if settings.verbose:
            _ = monitor_log_file(settings.gkfs_proxy_err, "Error Proxy")

    if not settings.exclude_proxy:
        jit_print(f"[green]############## Proxy init finished ##############\n\n\n\n ")


#! start Cargo
#!###############################
def start_cargo(settings: JitSettings) -> None:
    """Starts the Cargo component.

    Args:
        settings (JitSettings): jit settings
    """
    if settings.exclude_cargo:
        jit_print(
            f"[bold yellow]############## Skipping Cargo [/][black][{get_time()}][/]"
        )
    else:
        jit_print(
            f"[bold green]############## Starting Cargo [/][black][{get_time()}][/]"
        )

        if settings.cluster:
            call = (
                f"{settings.cargo_bin}/cargo "
                f"--listen {settings.gkfs_daemon_protocol}://ib0:{settings.port_cargo} -b 65536"
            )
            call = flaged_call(
                settings,
                call,
                settings.app_nodes,
                settings.procs_cargo,
                exclude=["ftio", "demon_log", "preload", "proxy"],
            )

        else:
            # if settings.debug_lvl > 0:
            #     debug_flag = "CARGO_LOG_LEVEL=trace"
            # else:
            #     debug_flag = "CARGO_LOG_LEVEL=debug"
            debug_flag = ""

            # Command for non-cluster
            call = f"{debug_flag} {settings.cargo_bin}/cargo --listen {settings.gkfs_daemon_protocol}://{settings.address_cargo}:{settings.port_cargo} -b 65536"
            call = flaged_call(
                settings,
                call,
                1,
                settings.procs_cargo,
                exclude=["ftio", "demon_log", "preload", "proxy"],
            )

        jit_print("[cyan]Starting Cargo[/]")

        # p_cargo = multiprocessing.Process(target=execute_background,args=(call, settings.cargo_log, settings.cargo_err, settings.dry_run))
        # p_cargo.start()
        # if settings.verbose:
        #     _ = monitor_log_file(settings.cargo_log,"Cargo")
        # if settings.verbose_error:
        #     _ = monitor_log_file(settings.cargo_err,"Error Cargo")

        process = execute_background_and_log(
            settings, call, settings.cargo_log, "cargo", settings.cargo_err
        )
        if settings.verbose_error:
            _ = monitor_log_file(settings.cargo_err, "Error Cargo")

        # wait for line to appear
        time.sleep(2)
        flag = wait_for_line(
            settings.cargo_log, "Start up successful", dry_run=settings.dry_run
        )
        if not flag:
            handle_sigint(settings)

        time.sleep(4)

    if not settings.exclude_cargo:
        jit_print(f"[green]############## Cargo init finished ##############\n\n\n\n ")


#! start FTIO
#!##############################
def start_ftio(settings: JitSettings) -> None:
    """Starts the FTIO component.

    Args:
        settings (JitSettings): jit settings
    """
    if settings.exclude_ftio or settings.exclude_all:
        jit_print(
            f"[bold yellow]############## Skipping FTIO [/][black][{get_time()}][/]"
        )

        relevant_files(settings)

        if settings.cluster and not settings.exclude_cargo:
            jit_print(
                "[bold yellow]Executing the calls below used later for staging out[/]"
            )
            call_0 = (
                f"srun --jobid={settings.job_id} {settings.single_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_bin}/cargo_ftio "
                f"--server {settings.gkfs_daemon_protocol}://{settings.address_cargo}:{settings.port_cargo} --run"
            )
            call_1 = (
                f"srun --jobid={settings.job_id} {settings.single_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_bin}/ccp "
                f"--server {settings.gkfs_daemon_protocol}://{settings.address_cargo}:{settings.port_cargo} --input / --output {settings.stage_out_path} "
                f"--if gekkofs --of {settings.cargo_mode}"
            )

            _ = execute_block(call_0, dry_run=settings.dry_run)
            _ = execute_block(call_1, dry_run=settings.dry_run)
    else:
        jit_print(f"[bold green]############## Starting FTIO [/][black][{get_time()}][/]")

        relevant_files(settings)

        ftio_data_staget_args = ""
        if settings.exclude_cargo:
            ftio_data_staget_args += (
                f"--stage_out_path {settings.stage_out_path} --stage_in_path {settings.stage_in_path} "
                f"--ld_preload {settings.gkfs_intercept} --host_file {settings.gkfs_hostfile} --gkfs_mntdir {settings.gkfs_mntdir} "
            )

            if settings.regex_match:
                ftio_data_staget_args += f"--adaptive '{settings.adaptive}' "

            if settings.adaptive:
                ftio_data_staget_args += f"--regex '{settings.regex_match}' "

            if settings.ignore_mtime:
                ftio_data_staget_args += "--ignore_mtime "

            if settings.parallel_move:
                ftio_data_staget_args += "--parallel_move "

            if settings.debug_lvl > 0:
                ftio_data_staget_args += "--debug "

        else:
            ftio_data_staget_args += (
                f"--cargo --cargo_bin {settings.cargo_bin} "
                f"--cargo_server {settings.gkfs_daemon_protocol}://{settings.address_cargo}:{settings.port_cargo} --stage_out_path {settings.stage_out_path} -t 0.2"
            )

        if settings.cluster:
            jit_print(
                f"[cyan]FTIO started on node {settings.ftio_node}, remaining nodes for the application: {settings.app_nodes} each with {settings.procs_ftio} processes [/]"
            )
            jit_print(
                f"[cyan]FTIO is listening node is {settings.address_ftio}:{settings.port_ftio} [/]"
            )
            call = (
                f"srun --jobid={settings.job_id} {settings.ftio_node_command} "
                f"--disable-status -N 1 --ntasks=1 --cpus-per-task={settings.procs_ftio} "
                f"--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 "
                f"{settings.ftio_bin_location}/predictor_jit {ftio_data_staget_args} --  --zmq_address {settings.address_ftio} --zmq_port {settings.port_ftio} {settings.ftio_args} "
            )
        else:
            check_port(settings)
            call = f"{settings.ftio_bin_location}/predictor_jit {ftio_data_staget_args} --  --zmq_address {settings.address_ftio} --zmq_port {settings.port_ftio} {settings.ftio_args} "

        jit_print("[cyan]Starting FTIO[/]")

        _ = execute_background_and_log(
            settings, call, settings.ftio_log, "ftio", settings.ftio_err
        )
        if settings.verbose_error:
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
    if not settings.exclude_ftio:
        jit_print(f"[green]############## FTIO init finished ##############\n\n\n\n ")


#! Stage in
#!##############################
def stage_in(settings: JitSettings, runtime: JitTime) -> None:
    """Stages data in from the specified path.

    Args:
        settings (JitSettings): jit settings
        runtime (JitTime): runtime object to track elapsed time
    """
    if settings.exclude_all:
        jit_print(
            f"[bold yellow]############## Skipping Stage in [/][black][{get_time()}][/]"
        )
    else:
        jit_print(f"[bold green]############## Staging in [/][black][{get_time()}][/]")
        adjust_regex(settings, "stage_in")

        # remove locks
        jit_print("[cyan]Cleaning locks")
        if settings.stage_in_path:
            execute_block(
                f"cd {settings.stage_in_path} && rm -f  $(find .  | grep .lock)"
            )

        jit_print(f"[cyan]Staging in to {settings.stage_in_path}", True)

        if True:  # settings.exclude_cargo:  # settings.exclude_cargo:
            # check that there are actually files
            call = ""
            if (
                len(
                    subprocess.check_output(
                        f"ls -R {settings.stage_in_path}/", shell=True
                    ).decode()
                )
                > 0
            ):
                call = flaged_call(
                    settings,
                    f"cp  -r {settings.stage_in_path}/* {settings.gkfs_mntdir}",
                    exclude=["ftio"],
                )
                # or faster
                # copy_procs = max(10, int(settings.procs_app / 2))
                # call = flaged_call(
                #     settings,
                #     procs_per_node=copy_procs,
                #     call=(
                #         "bash -c "
                #         f'"STAGE_IN_SRC={settings.stage_in_path}; '
                #         f"STAGE_IN_DST={settings.gkfs_mntdir}; "
                #         f'find \\"$STAGE_IN_SRC\\" -type f | xargs -n 1 -P {copy_procs} cp --parents -t \\"$STAGE_IN_DST\\""'
                #     ),
                #     exclude=["ftio"],
                # )

            start = time.time()
            _ = execute_block(call, dry_run=settings.dry_run)
        # TODO: fix cpp cargo
        else:
            if settings.cluster:
                call = flaged_call(
                    settings,
                    f"{settings.cargo_bin}/ccp --server {settings.gkfs_daemon_protocol}://{settings.address_cargo}:{settings.port_cargo} --output / --input {settings.stage_in_path} --of gekkofs --if {settings.cargo_mode}",
                    exclude=["ftio"],
                )
                # call = f"srun --jobid={settings.job_id} {settings.single_node_command} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 "
            else:
                call = f"mpiexec -x LIBGKFS_ENABLE_METRICS=off -np 1 --oversubscribe {settings.cargo_bin}/ccp --server {settings.gkfs_daemon_protocol}://{settings.address_cargo}:{settings.port_cargo} --output / --input {settings.stage_in_path} --of gekkofs --if {settings.cargo_mode}"

            start = time.time()

            execute_background_and_wait_line(
                call,
                settings.cargo_log,
                "retval: CARGO_SUCCESS, status: {state: completed",
                settings.dry_run,
            )

        elapsed_time(settings, runtime, "Stage in", time.time() - start)
        check(settings)
        # adjust regex for flushing
        adjust_regex(settings, "flush")
    if not settings.exclude_all:
        jit_print(f"[green]############## Stage-in finished ##############\n\n\n\n ")


#! Stage out
#!##############################
def stage_out(settings: JitSettings, runtime: JitTime) -> None:
    """Stages data out to the specified path.

    Args:
        settings (JitSettings): jit settings
        runtime (JitTime): runtime object to track elapsed time
    """
    if settings.exclude_all:
        jit_print(
            f"[bold yellow]############## Skipping  Stage out [/][black][{get_time()}][/]"
        )
    else:

        jit_print(
            f"[bold green]############## Staging out [/][black][{get_time()}][/]\n",
            f"[cyan]Moving data from {settings.gkfs_mntdir} -> {settings.stage_out_path}[/]",
        )
        adjust_regex(settings, "stage_out")

        if settings.exclude_cargo:
            # call = flaged_call(
            #     settings,
            #     f"cp -r  {settings.gkfs_mntdir} {settings.stage_out_path} || echo 'nothing to stage out'",
            #     exclude=["ftio"],
            # )
            start = time.time()
            # _ = execute_block(call, dry_run=settings.dry_run)

            #  give ftio slightly more time to finish moving
            if not settings.exclude_ftio:
                jit_print("[cyan]Shutting down FTIO as application finished")
                shut_down(settings, "FTIO", settings.ftio_pid)

            jit_move(settings)
            elapsed_time(settings, runtime, "Stage out", time.time() - start)
        else:

            if not settings.dry_run:
                try:
                    call = flaged_call(
                        settings,
                        f"ls -R {settings.gkfs_mntdir}",
                        exclude=["ftio"],
                    )
                    files = subprocess.check_output(call, shell=True).decode()
                    jit_print(f"[cyan]gekko_ls {settings.gkfs_mntdir}: \n{files}[/]")
                except Exception as e:
                    jit_print(f"[red] Error during test:\n{e}")

            # Reset relevant files
            if settings.cluster:
                call = (
                    f"srun --jobid={settings.job_id} {settings.single_node_command} "
                    f"--disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 "
                    f"--overcommit --overlap --oversubscribe --mem=0 {settings.cargo_bin}/cargo_ftio "
                    f"--server {settings.gkfs_daemon_protocol}://{settings.address_cargo}:{settings.port_cargo} --run"
                )
            else:
                call = (
                    f"mpiexec -np 1 --oversubscribe {settings.cargo_bin}/cargo_ftio "
                    f"--server {settings.gkfs_daemon_protocol}://{settings.address_cargo}:{settings.port_cargo} --run"
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
    if not settings.exclude_all:
        jit_print(f"[green]############## Stage-Out finished ##############\n\n\n\n ")


#! App call
#!##############################
def start_application(settings: JitSettings, runtime: JitTime):
    """Starts the application specified in the settings.

    Args:
        settings (JitSettings): jit settings
        runtime (JitTime): runtime object to track elapsed time
    """
    name = (
        settings.app_call.split("/", 1)[1]
        if "/" in settings.app_call
        else settings.app_call
    )
    jit_print(
        f"[green bold]############## Executing Application {name} [/][black][{get_time()}][/]"
    )
    # set up dir
    original_dir = settings.dir
    jit_print(f" Current directory {original_dir}")
    if not settings.dry_run:
        check_setup(settings)
        # pass

    if settings.cluster:
        additional_arguments = ""
        if settings.use_mpirun:
            if not settings.exclude_ftio:
                additional_arguments += f"-x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port_ftio} -x LIBGKFS_ENABLE_METRICS=on -x LIBGKFS_METRICS_FLUSH_INTERVAL=5 "
            if not settings.exclude_proxy:
                additional_arguments += (
                    f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
                )
            if not settings.exclude_daemon:
                if settings.debug_lvl > 0:
                    log_modules = "all"
                else:
                    log_modules = "info,warnings,errors"
                additional_arguments += (
                    f"-x LIBGKFS_LOG={log_modules} "
                    f"-x LIBGKFS_LOG_OUTPUT={settings.gkfs_client_log} "
                    f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                    f"-x LD_PRELOAD={settings.gkfs_intercept} "
                )

            if (settings.lock_generator and not settings.exclude_daemon) or (
                settings.lock_consumer and not settings.exclude_cargo
            ):
                additional_arguments += get_env(settings, "mpi")

            call = (
                # f" cd {settings.run_dir} && "
                # f"strace -f -e trace=read,write,open,close,stat,fstat,lseek,access -o /gpfs/fs1/home/tarrafah/strace_n{settings.app_nodes}_p{settings.procs_app}.txt mpiexec -np {settings.app_nodes*settings.procs_app} --oversubscribe "
                # f" cd {settings.run_dir} && time -p mpiexec --mca errhandler ftmpi --mca mpi_abort_print_stack 1  -np {settings.app_nodes*settings.procs_app} --oversubscribe "
                # ssh {settings.single_node} 'pwd && cd {settings.run_dir} && pwd  && ls && hostname
                f" cd {settings.run_dir} && time -p  mpiexec -np {settings.app_nodes*settings.procs_app} --oversubscribe "
                f"--hostfile {settings.mpi_hostfile} --map-by node "
                f"{additional_arguments} "
                f"{settings.task_set_1} {settings.app_call} {settings.app_flags}"
            )
        else:
            if not settings.exclude_ftio:
                additional_arguments += f"LIBGKFS_ENABLE_METRICS=on,LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port_ftio},LIBGKFS_METRICS_FLUSH_INTERVAL=5,"
            if not settings.exclude_proxy:
                additional_arguments += (
                    f"LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile},"
                )
            if not settings.exclude_daemon:
                additional_arguments += (
                    # f"LIBGKFS_LOG=info,warnings,errors,syscalls"
                    f"LIBGKFS_LOG=all,"
                    f"LIBGKFS_LOG_OUTPUT={settings.gkfs_client_log},"
                    f"LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile},"
                    f"LD_PRELOAD={settings.gkfs_intercept},"
                )
                if (
                    not settings.exclude_cargo and settings.lock_generator
                ):  # if gekko and cargo active
                    additional_arguments += get_env(settings, "srun")

            app_call = get_executable_realpath(settings.app_call, settings.run_dir)
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
            jit_print(f"Changing directory to  {os.getcwd()}")

        additional_arguments = ""
        if not settings.exclude_ftio:
            additional_arguments += f"-x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port_ftio} -x LIBGKFS_ENABLE_METRICS=on "
        if not settings.exclude_proxy:
            additional_arguments += (
                f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
            )
        if not settings.exclude_daemon:
            additional_arguments += (
                f"-x LIBGKFS_LOG=info,warnings,errors "
                f"-x LIBGKFS_LOG_OUTPUT={settings.gkfs_client_log} "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f"-x LD_PRELOAD={settings.gkfs_intercept} "
            )
            if (
                not settings.exclude_cargo and settings.lock_generator
            ):  # if gekko and cargo active
                additional_arguments += get_env(settings, "mpi")

        call = (
            f" time  mpiexec -np {int(settings.procs_app)} --oversubscribe "
            f"{additional_arguments} {settings.app_call} {settings.app_flags}"
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
    # monitor log
    if settings.verbose:
        _ = monitor_log_file(settings.app_log, "")

    # monitor error
    if settings.verbose_error:
        _ = monitor_log_file(settings.app_err, f"{name} error")

    _, stderr = process.communicate()

    # get the real time
    # The timing result will be in stderr because 'time' outputs to stderr by default

    # Extract the 'real' time from the output
    real_time = time.time() - start
    real_time = extract_accurate_time(settings, real_time)

    elapsed_time(settings, runtime, "App", real_time)

    if process.returncode != 0:
        jit_print(f"[red]Error executing command:{call}")
        jit_print(f"[red]Error was:\n{stderr}")
        exit_routine(settings)
    else:
        pass

    if not settings.exclude_ftio and settings.exclude_cargo:
        jit_print("[cyan]Shuting down FTIO as application finished")
        shut_down(settings, "FTIO", settings.ftio_pid)

    os.chdir(original_dir)
    jit_print(f"Changing directory to {os.getcwd()}")

    jit_print(f"[green]############## Application finished ##############\n\n\n\n ")


#! Pre app call
#!##############################
def pre_call(settings: JitSettings) -> None:
    """Executes pre-application calls specified in the settings.

    Args:
        settings (JitSettings): jit settings
    """
    if settings.pre_app_call:
        jit_print(
            f"[green bold]############## Pre-application Call [/][black][{get_time()}][/]"
        )
        if isinstance(settings.pre_app_call, str):
            call = settings.pre_app_call
            if any(x in call for x in ["mpiex", "mpirun"]):
                call = flaged_call(settings, call, exclude=["ftio"])
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
                    call = flaged_call(settings, call, exclude=["ftio"])
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
        jit_print(
            f"[green]############## Pre-application call finished ##############\n\n\n\n "
        )


#! Post app call
#!##############################
def post_call(settings: JitSettings) -> None:
    """Executes post-application calls specified in the settings.

    Args:
        settings (JitSettings): jit settings
    """
    if settings.post_app_call:
        jit_print(
            f"[green bold]############## Post-application Call [/][black][{get_time()}][/]"
        )
        additional_arguments = ""
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
        jit_print(
            f"[green]############## Post-application call finished ##############\n\n\n\n "
        )
