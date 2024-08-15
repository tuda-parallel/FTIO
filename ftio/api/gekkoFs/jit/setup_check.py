import os
import time
from rich.console import Console
from ftio.api.gekkoFs.jit.execute_and_wait import execute_block
from ftio.api.gekkoFs.jit.jitsettings import JitSettings
console = Console()

def check_setup(settings:JitSettings):
    
    if not settings.exclude_all:

        # Display MPI hostfile
        if settings.cluster:
            mpi_hostfile_path = os.path.expanduser('~/hostfile_mpi')
            with open(mpi_hostfile_path, 'r') as file:
                mpi_hostfile_content = file.read()
            console.print(f"[cyan]>> MPI hostfile:\n{mpi_hostfile_content}[/]")

        # Display GekkoFS hostfile
        gekkofs_hostfile = settings.gkfs_hostfile
        with open(gekkofs_hostfile, 'r') as file:
            gekkofs_hostfile_content = file.read()
        console.print(f"[cyan]>> Gekko hostfile:\n{gekkofs_hostfile_content}[/]")

        
        # ls_command = f"LD_PRELOAD={settings.gkfs_intercept} LIBGKFS_HOSTS_FILE={gekkofs_hostfile} ls {settings.gkfs_mntdir}"
        # files = subprocess.check_output(ls_command, shell=True).decode()
        # console.print(f"[cyan]>> geko_ls {gkfs_mntdir}: \n{files}[/]")

        if settings.cluster and settings.debug and not settings.exclude_demon:
            #srun dies not work with gekko
            # call = (
            #     f"srun --jobid={settings.jit_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} --ntasks={settings.app_nodes} "
            #     f"--cpus-per-task={settings.procs_demon} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 "
            #     f"--export=LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile},LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')},LD_PRELOAD={settings.gkfs_intercept} "
            #     f"/usr/bin/ls {settings.gkfs_mntdir} "
            # )
            # console.print("[bold green] JIT[/][cyan]>> Checking srun with Gekko")
            # out = execute_block(call, False)
            # console.print(f"srun check: {out}\n")


            additional_arguments = ""
            if not settings.exclude_ftio:
                additional_arguments += " -x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port} "
            if not settings.exclude_proxy:
                additional_arguments += " -x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
            call = (
                f"mpiexec -np 10 --oversubscribe "
                f"--hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=errors "
                f"-x LIBGKFS_ENABLE_METRICS=on  "
                f"-x LD_PRELOAD={settings.gkfs_intercept} "
                f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                f" echo -e 'Here is $(hostname): \\n$(/usr/bin/ls {settings.gkfs_mntdir})' "
            )
            console.print("[bold green] JIT[/][cyan]>> Checking mpiexec with Gekko")
            out = execute_block(call, False)
            console.print(f"srun check: {out}")
        else:
            console.print("[bold green] JIT[/][cyan]>> Skipping setup check")
        # # Run MPI exec test script
        # procs = settings.procs
        # if settings.cluster:
        #     test_script_command = (f"mpiexec -np {procs} --oversubscribe --hostfile {mpi_hostfile_path} "
        #                         f"--map-by node -x LIBGKFS_LOG=errors -x LD_PRELOAD={settings.gkfs_intercept} "
        #                         f"-x LIBGKFS_HOSTS_FILE={gekkofs_hostfile} -x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
        #                         f"/home/tarrafah/nhr-admire/tarraf/FTIO/ftio/api/gekkoFs/scripts/test.sh")
        #     console.print(f"[cyan]>> statx:[/]")
        #      subprocess.run(test_script_command, shell=True, text=True, capture_output=True, check=True, executable="/bin/bash"        )

                    
        #     srun_command = (f"srun --export=LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile},LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')},"
        #                     f"LD_PRELOAD={settings.gkfs_intercept} --jobid={settings.jit_id} {settings.app_nodes_command} --disable-status "
        #                     f"-N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 "
        #                     f"/usr/bin/ls {settings.gkfs_mntdir}")
        #     files2 = subprocess.check_output(srun_command, shell=True).decode()
        #     console.print(f"[cyan]>> srun ls {settings.gkfs_mntdir}: \n{files2}[/]")

        # Note: The commented out command for `mpirun` is not included in this translation.

    # Pause for 1 second
    time.sleep(1)
