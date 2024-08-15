import sys
import time
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
    start_gekko_demon,
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
    log_dir,
    print_settings,
    soft_kill,
)


console = Console()


def main() -> None:
    """Executes the jit script
    """

    console.print("\n\n[bold green]################ JIT ################[/]\n")
    settings = JitSettings()
    runtime = JitTime()

    # Parse options
    parse_options(settings, sys.argv[1:])

    # Handle kill signal
    signal.signal(signal.SIGINT, lambda signal, frame: handle_sigint(settings))

    # Clean other jobs
    cancel_jit_jobs()

    # Create folder for logs
    log_dir(settings)

    # 1. Allocate resources
    allocate(settings)
    
    # 1.2 Get the address
    get_address_ftio(settings)

    #1.3 Get address carg
    get_address_cargo(settings)

    # 1.4 Print settings
    print_settings(settings)

    # 2. Start Gekko Server (Daemon)
    start_gekko_demon(settings)

    # 2.1
    start_gekko_proxy(settings)

    # 3. Start Cargo Server
    start_cargo(settings)

    # 4. Stage in
    stage_in(settings, runtime)

    # 5. Start FTIO
    start_ftio(settings)

    # 6. Pre- and application with Gekko intercept
    pre_call(settings)
    start_application(settings, runtime)

    # 7. Stage out
    stage_out(settings, runtime)

    # 8. Post call if exists
    post_call(settings)

    # # 9. Display total time
    runtime.print_time()

    # 10. Soft kill
    soft_kill(settings)

    # 11. Hard kill
    hard_kill(settings)

    console.print(f"[bold green]############### JIT completed ###############[/]")
    sys.exit(0)


if __name__ == "__main__":
    main()
