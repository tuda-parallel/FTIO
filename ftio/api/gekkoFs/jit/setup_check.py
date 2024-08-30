import os
import time
from datetime import datetime
from rich.console import Console
from ftio.api.gekkoFs.jit.execute_and_wait import execute_block
from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.setup_helper import jit_print
console = Console()

def check_setup(settings:JitSettings):
    
    if not settings.exclude_all:

        # Display MPI hostfile
        if settings.cluster:
            mpi_hostfile_path = os.path.expanduser(f"{settings.app_dir}/hostfile_mpi")
            with open(mpi_hostfile_path, "r") as file:
                mpi_hostfile_content = file.read()
            console.print(f"[cyan]>> MPI hostfile:\n{mpi_hostfile_content}[/]")

        # Display GekkoFS hostfile
        gekkofs_hostfile = settings.gkfs_hostfile
        with open(gekkofs_hostfile, "r") as file:
            gekkofs_hostfile_content = file.read()
        console.print(f"[cyan]>> Geko hostfile:\n{gekkofs_hostfile_content}[/]")

        
        # ls_command = f"LD_PRELOAD={settings.gkfs_intercept} LIBGKFS_HOSTS_FILE={gekkofs_hostfile} ls {settings.gkfs_mntdir}"
        # files = subprocess.check_output(ls_command, shell=True).decode()
        # console.print(f"[cyan]>> geko_ls {gkfs_mntdir}: \n{files}[/]")

        if settings.cluster and settings.debug and not settings.exclude_demon:
            #srun dies not work with gekko
            # call = (
            #     f"srun --jobid={settings.job_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} --ntasks={settings.app_nodes} "
            #     f"--cpus-per-task={settings.procs_demon} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 "
            #     f"--export=LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile},LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')},LD_PRELOAD={settings.gkfs_intercept} "
            #     f"/usr/bin/ls {settings.gkfs_mntdir} "
            # )
            # jit_print("[cyan]>> Checking srun with Gekko")
            # out = execute_block(call, False)
            # console.print(f"srun check: {out}\n")


            additional_arguments = ""
            if not settings.exclude_ftio:
                additional_arguments += f"-x LIBGKFS_METRICS_IP_PORT={settings.address_ftio}:{settings.port} -x LIBGKFS_ENABLE_METRICS=on "
            if not settings.exclude_proxy:
                additional_arguments += f"-x LIBGKFS_PROXY_PID_FILE={settings.gkfs_proxyfile} "
            if not settings.exclude_demon:
                additional_arguments += (
                    f"-x LIBGKFS_LOG=info,warnings,errors "
                    f"-x LIBGKFS_LOG_OUTPUT={settings.gekko_client_log} "
                    f"-x LIBGKFS_HOSTS_FILE={settings.gkfs_hostfile} "
                    f"-x LD_PRELOAD={settings.gkfs_intercept} "
                    )


            #test script
            jit_print("[cyan] >> Checking test file")
            try:
                timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
                file = create_test_file("test.sh"+timestamp, settings)
                call = (
                        f" mpiexec -np {settings.app_nodes} --oversubscribe "
                        f"--hostfile {settings.app_dir}/hostfile_mpi --map-by node "
                        f"{additional_arguments} "
                        
                        f"{file}"
                    )
                out = execute_block(call, False)
                console.print(f"{out}")
                # remove the created file
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                jit_print(f"[red] >> Error running test script:\n{e}")
        else:
            jit_print("[cyan]>> Skipping setup check")
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
        #                     f"LD_PRELOAD={settings.gkfs_intercept} --jobid={settings.job_id} {settings.app_nodes_command} --disable-status "
        #                     f"-N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 "
        #                     f"/usr/bin/ls {settings.gkfs_mntdir}")
        #     files2 = subprocess.check_output(srun_command, shell=True).decode()
        #     console.print(f"[cyan]>> srun ls {settings.gkfs_mntdir}: \n{files2}[/]")

        # Note: The commented out command for `mpirun` is not included in this translation.

    # Pause for 1 second
    time.sleep(1)



def create_test_file(name:str, settings:JitSettings) -> str:
    # Define the content of the shell script
    script_content = "#!/bin/bash\n"
    script_content +="myhostname=$(hostname)\n"
    script_content +=f"statcall=$(stat {settings.gkfs_mntdir})\n"
    if settings.app_nodes == 1:
        script_content +=f"lscall=$(ls -lR {settings.gkfs_mntdir})\n"
    else:
        script_content +=f"lscall=$(ls {settings.gkfs_mntdir})\n"
    script_content += """
    echo -e "Hello I am ${myhostname} and stat output: \\n${statcall}\\n The directory contains:\\n${lscall}\\n"
    """

    # Write the content to a file called tet.sh
    file_path = os.path.join(os.getcwd(), name)
    with open(file_path, "w") as file:
        file.write(script_content)

    os.chmod(file_path, 0o755)
    return file_path