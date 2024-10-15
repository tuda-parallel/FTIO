from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.setup_helper import jit_print, create_hostfile
from ftio.api.gekkoFs.jit.execute_and_wait import execute_block

def init_gekko(settings: JitSettings) -> None:
    """Creates GekkoFs hostfile and directories (root and mount)

    Args:
        settings (JitSettings): Jit settings
    """
    if not settings.exclude_daemon:
        create_hostfile(settings)
        # set debug flag
        if settings.cluster:
            # Create directories
            # call_0 = f"srun --jobid={settings.job_id} {settings.single_node_command} -N 1 --ntasks=1 mkdir -p {settings.gkfs_mntdir}"
            call_0 =(
                f"srun --jobid={settings.job_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs_daemon} --ntasks-per-node=1 --overcommit --overlap "
                f"--oversubscribe --mem=0 mkdir -p {settings.gkfs_mntdir}"
                    )
            call_1 =(
                f"srun --jobid={settings.job_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
                f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs_daemon} --ntasks-per-node=1 --overcommit --overlap "
                f"--oversubscribe --mem=0 mkdir -p {settings.gkfs_rootdir}"
                    )
        else:
            call_0 = f"mkdir -p {settings.gkfs_mntdir}"
            call_1 = f"mkdir -p {settings.gkfs_rootdir}"

        jit_print("[cyan]>> Creating directories[/]")
        _ = execute_block(call_0)
        _ = execute_block(call_1)