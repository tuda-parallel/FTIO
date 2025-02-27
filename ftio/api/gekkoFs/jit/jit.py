"""
This file contains the main function to execute the JIT script.
It sets up the environment, allocates resources, starts necessary services,
and manages the workflow from staging in to staging out.
"""

import sys
import signal
from rich.console import Console
from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.jittime import JitTime
from ftio.api.gekkoFs.jit.setup_core import (
    post_call,
    pre_call,
    stage_in,
    stage_out,
    start_application,
    start_cargo,
    start_ftio,
    start_gekko_daemon,
    start_gekko_proxy,
)
from ftio.api.gekkoFs.jit.setup_helper import (
    get_address_cargo,
    get_address_ftio,
    handle_sigint,
    hard_kill,
    parse_options,
    cancel_jit_jobs,
    allocate,
    # set_env,
    log_dir,
    print_settings,
    save_bandwidth,
    set_dir_gekko,
    soft_kill,
)


console = Console()


def main() -> None:
    """Executes the JIT script by setting up the environment, 
    allocating resources, starting necessary services, 
    and managing the workflow from staging in to staging out.
    """

    console.print("\n\n[bold green]################ JIT ################[/]\n")
    settings = JitSettings()
    runtime = JitTime()

    # Parse options
    parse_options(settings, sys.argv[1:])

    # Handle kill signal
    signal.signal(signal.SIGINT, lambda signal, frame: handle_sigint(settings))

    # Clean other jobs
    cancel_jit_jobs(settings)

    # # 1.0 set env variables
    # set_env(settings)

    # 1.1 Allocate resources
    allocate(settings)

    # 1.2 Create folder for logs
    log_dir(settings)
    
    # 1.3 Get the address
    get_address_ftio(settings)

    # 1.4 Get address carg
    get_address_cargo(settings)

    # 1.5 Set Gekko Root dir
    set_dir_gekko(settings)

    # 1.6 Print settings
    print_settings(settings)

    # 2.0 Start Gekko Server (Daemon)
    start_gekko_daemon(settings)

    # 2.1 Start Proxy
    start_gekko_proxy(settings)

    # 3.0 Start Cargo Server
    start_cargo(settings)

    # 4.0 Stage in
    stage_in(settings, runtime)

    # 5.0 Start FTIO
    start_ftio(settings)

    # 6.0 Pre- and application with Gekko intercept
    pre_call(settings)
    start_application(settings, runtime)

    # 7.0 Stage out
    stage_out(settings, runtime)

    # 8.0 Post call if exists
    post_call(settings)

    # 9.0 Display total time
    # _ = runtime.print_time()
    runtime.print_and_save_time(settings)

    # save_bandwidth
    save_bandwidth(settings)

    # 11.0 Soft kill
    soft_kill(settings)

    # 12.0 Hard kill
    hard_kill(settings)

    console.print("[bold green]############### JIT completed ###############[/]")
    sys.exit(0)


if __name__ == "__main__":
    main()
