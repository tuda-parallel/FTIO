from ftio.api.gekkoFs.jit.jitsettings import JitSettings
from ftio.api.gekkoFs.jit.setup_helper import flaged_call, jit_print, create_hostfile
from ftio.api.gekkoFs.jit.execute_and_wait import execute_block

def init_gekko(settings: JitSettings) -> None:
    """Creates GekkoFs hostfile and directories (root and mount)

    Args:
        settings (JitSettings): Jit settings
    """
    if not settings.exclude_daemon:
        create_hostfile(settings)
        calls =[]
        # set debug flag
        # if settings.cluster:
        #     # Create directories
        #     calls.append(
        #         f"srun --jobid={settings.job_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
        #         f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs_daemon} --ntasks-per-node=1 --overcommit --overlap "
        #         f"--oversubscribe --mem=0 mkdir -p {settings.gkfs_mntdir}"
        #             )
        #     calls.append(
        #         f"srun --jobid={settings.job_id} {settings.app_nodes_command} --disable-status -N {settings.app_nodes} "
        #         f"--ntasks={settings.app_nodes} --cpus-per-task={settings.procs_daemon} --ntasks-per-node=1 --overcommit --overlap "
        #         f"--oversubscribe --mem=0 mkdir -p {settings.gkfs_rootdir}"
        #             )
        # else:
        #     calls.append(f"mkdir -p {settings.gkfs_mntdir}")
        #     calls.append(f"mkdir -p {settings.gkfs_rootdir}")
        calls.append(f"mkdir -p {settings.gkfs_mntdir}")
        calls.append(f"mkdir -p {settings.gkfs_rootdir}")
        jit_print("[cyan]>> Creating directories[/]")
        for call in calls:
            tmp = flaged_call(settings, call, nodes=settings.app_nodes, procs_per_node=1, exclude=["ftio","demon", "proxy","cargo"])
            _ = execute_block(tmp)


