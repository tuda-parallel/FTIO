import os
import socket
import numpy as np
from rich.console import Console

console = Console()


class JitSettings:
    def __init__(self) -> None:
        """sets the internal variables, don't modify this part (except flags if needed).
        only Adjust the paths in the function set_variables
        """
        
        # flags
        ##############
        self.set_tasks_affinity = True
        self.gkfs_daemon_protocol = "ofi+verbs" #"ofi+sockets"  or "ofi+verbs"
        self.cargo_mode = "parallel" #"parallel" or "posix"
        self.debug = True
        self.verbose = True
        self.node_local = False # execute in node local space        

        # Variable initialization (don't change)
        ################
        self.dry_run = False 
        self.log_suffix = "DPCF"
        self.app_dir = ""
        self.cluster = False
        self.job_id = 0
        self.static_allocation = False
        self.ftio_node = ""
        self.single_node = ""
        self.app_nodes = 0
        self.all_nodes = 0
        self.app_nodes_command = ""
        self.ftio_node_command = ""
        self.single_node_command = ""

        self.log_dir = ""
        self.gekko_daemon_log = ""
        self.gekko_daemon_err = ""
        self.gekko_proxy_log = ""
        self.gekko_proxy_err = ""
        self.gekko_client_log = ""
        self.cargo_log = ""
        self.cargo_err = ""
        self.ftio_log = ""
        self.ftio_err = ""
        self.app_log = ""
        self.app_err = ""

        # exclude flags
        self.exclude_ftio = False
        self.exclude_cargo = False
        self.exclude_daemon = False
        self.exclude_proxy = True
        self.exclude_all = False

        # pid of processes
        self.ftio_pid = 0
        self.gekko_daemon_pid = 0
        self.gekko_proxy_pid = 0
        self.cargo_pid = 0
        self.log_speed = 0.1

        # parsed variables
        ###################
        self.address_ftio = "127.0.0.1"
        self.address_cargo = "127.0.0.1"
        self.port = "5555"
        self.nodes = 1
        self.max_time = 30
        self.skip_confirm = False
        self.trap_exit = True
        self.soft_kill = True
        self.hard_kill = True

        self.procs = os.cpu_count() or 128
        self.omp_threads = 64
        self.task_set_0 = ""
        self.task_set_1 = ""
        self.procs_daemon = 0
        self.procs_proxy = 0
        self.procs_cargo = 0
        self.procs_app = 0
        self.procs_ftio = 0

        self.set_cluster_mode()
        self.set_default_procs()
        self.set_variables()

    def set_cluster_mode(self) -> None:
        """automatically identifies if it's a cluster or local machine"""
        hostname = socket.gethostname()
        if "cpu" in hostname or "mogon" in hostname:
            self.cluster = True
            if "mogon" in hostname:
                console.print(
                    "[bold red] Execute this script on CPU nodes\n mpiexec still has some bugs[/]"
                )

        console.print(f"[bold green]JIT >> CLUSTER MODE: {self.cluster}[/]")

    def update(self) -> None:
        """updates the flags and pass variables after the passed options are read.
        This is necessary, to adapt to the cluster mode and the installation path
        """
        self.set_flags()
        self.set_variables()
        self.set_absolute_path()
        self.update_settings()

    def update_settings(self):
        if self.dry_run:
            new_name = "Dry_" + self.job_name
            self.alloc_call_flags = self.alloc_call_flags.replace(
                self.job_name, new_name
            )
            self.job_name = new_name

    def set_absolute_path(self) -> None:
        self.app_dir = os.path.expanduser(self.app_dir)
        self.ftio_bin_location = os.path.expanduser(self.ftio_bin_location)

    def set_default_procs(self) -> None:
        # default values for the procs in proc_list is not passed
        if self.cluster:
            self.procs_proxy = int(np.floor(self.procs / 2))
            self.procs_daemon = int(np.floor(self.procs / 2))
            self.procs_cargo = 2
            self.procs_ftio = self.procs
            self.procs_app = int(np.floor(self.procs / 2))
        else:
            self.procs = 10
            self.procs_daemon = 1
            self.procs_proxy = 1
            self.procs_cargo = 2
            self.procs_ftio = 1
            self.procs_app = self.procs

    def update_geko_files(self):
        if not self.exclude_daemon:
            self.gkfs_hostfile = self.gkfs_hostfile.replace(
                ".txt", f"_{self.job_id}.txt"
            )
        if not self.exclude_proxy:
            self.gkfs_proxyfile = self.gkfs_proxyfile.replace(
                ".pid", f"_{self.job_id}.pid"
            )

    def set_flags(self) -> None:
        """sets the flags in case exclude all is specified
        in the options passed
        """

        if (
            self.exclude_ftio
            and self.exclude_cargo
            and self.exclude_daemon
            and self.exclude_proxy
        ):
            self.exclude_all = True
            

        if self.exclude_all:
            self.exclude_ftio = True
            self.exclude_cargo = True
            self.exclude_daemon = True
            self.exclude_proxy = True
            

        if not self.cluster:
            if self.nodes > 1:
                self.procs = self.nodes
                self.nodes = 1
                console.print(
                    f"[bold green]JIT [bold cyan]>> correcting nodes to {self.nodes} and processes to {self.procs} [/]"
                )
        self.log_suffix = "DPCF"
        if self.exclude_daemon:
            self.procs_daemon = 0
            self.log_suffix =  self.log_suffix.replace("D","")
        if self.exclude_proxy:
            self.procs_proxy = 0
            self.log_suffix =  self.log_suffix.replace("P","")
        if self.exclude_cargo:
            self.procs_cargo = 0
            self.log_suffix =  self.log_suffix.replace("C","")
        if self.exclude_ftio:
            self.procs_ftio = 0
            self.log_suffix =  self.log_suffix.replace("F","")

        if self.set_tasks_affinity:
            self.task_set_0 = f"taskset -c 0-{np.floor(self.procs/2)-1:.0f}"
            if self.procs - np.floor(self.procs / 2) >= self.procs_app:
                self.task_set_1 = (
                    f"taskset -c {np.ceil(self.procs/2):.0f}-{self.procs-1:.0f}"
                )

    def set_log_dirs(self):
        self.gekko_daemon_log = os.path.join(self.log_dir, "gekko_daemon.log")
        self.gekko_daemon_err = os.path.join(self.log_dir, "gekko_daemon.err")
        self.gekko_proxy_log = os.path.join(self.log_dir, "gekko_proxy.log")
        self.gekko_proxy_err = os.path.join(self.log_dir, "gekko_proxy.err")
        self.gekko_client_log = os.path.join(self.log_dir, "gekko_client.log")
        self.cargo_log = os.path.join(self.log_dir, "cargo.log")
        self.cargo_err = os.path.join(self.log_dir, "cargo.err")
        self.ftio_log = os.path.join(self.log_dir, "ftio.log")
        self.ftio_err = os.path.join(self.log_dir, "ftio.err")
        self.app_log = os.path.join(self.log_dir, "app.log")
        self.app_err = os.path.join(self.log_dir, "app.err")

    def to_dict(self):  # -> dict[str, Any]:
        return {
            "nodes": self.nodes,
            "app nodes": self.app_nodes,
            "procs": self.procs,
            "procs daemon": self.procs_daemon,
            "procs proxy": self.procs_proxy,
            "procs cargo": self.procs_cargo,
            "procs app  ": self.procs_app,
            "procs ftio ": self.procs_ftio,
            "task_set_0": self.task_set_0,
            "task_set_1": self.task_set_1,
            "OpenMP threads": self.omp_threads,
            "protocol": self.gkfs_daemon_protocol,
            "app dir": self.app_dir,
            "app call": self.app_call,
            "id": self.job_id,
            "mode": self.log_suffix,
        }

    #!##########################
    #! only modify here
    #!##########################
    def set_variables(self) -> None:
        """sets the path variables"""
        # ****** install location ******
        if self.cluster:
            self.install_location = "/beegfs/home/Shared/admire/JIT"

        # ****** job allocation call ******
        # self.alloc_call_flags = "--overcommit --oversubscribe --partition parallel -A nhr-admire --job-name JIT --no-shell --exclude=cpu0082"
        self.job_name = "JIT"
        self.alloc_call_flags = f"--overcommit --oversubscribe --partition largemem -A nhr-admire --job-name {self.job_name} --no-shell --exclude=cpu0081,cpu0082,cpu0083,cpu0084"

        # ? TOOLS
        # ?#######################
        # ****** ftio variables ******
        self.ftio_bin_location = "/lustre/project/nhr-admire/tarraf/FTIO/.venv/bin"

        # ****** gkfs variables ******
        self.gkfs_daemon    = "/lustre/project/nhr-admire/tarraf/deps/gekkofs_zmq_install/bin/gkfs_daemon"
        self.gkfs_intercept = "/lustre/project/nhr-admire/tarraf/deps/gekkofs_zmq_install/lib64/libgkfs_intercept.so"
        self.gkfs_mntdir    = "/dev/shm/tarraf_gkfs_mountdir"
        self.gkfs_rootdir   = "/dev/shm/tarraf_gkfs_rootdir"
        self.gkfs_hostfile  = "/lustre/project/nhr-admire/tarraf/gkfs_hosts.txt"
        self.gkfs_proxy     = "/lustre/project/nhr-admire/tarraf/gekkofs/build/src/proxy/gkfs_proxy"
        self.gkfs_proxyfile = "/dev/shm/tarraf_gkfs_proxy.pid"


        # ****** cargo variables ******
        self.cargo        = "/lustre/project/nhr-admire/tarraf/deps/gekkofs_zmq_install/bin/cargo"#"/lustre/project/nhr-admire/tarraf/cargo/build/src/cargo"
        self.cargo_cli    = "/lustre/project/nhr-admire/tarraf/deps/gekkofs_zmq_install/bin"#"/lustre/project/nhr-admire/tarraf/cargo/build/cli"
        self.cargo_server = f"{self.gkfs_daemon_protocol}://127.0.0.1:62000"

        # ? APP settings
        # ?##########################
        # ****** app call ******
        #  ├─ IOR
        # self.app="/lustre/project/nhr-admire/tarraf/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
        # self.app="/lustre/project/nhr-admire/tarraf/HACC-IO/HACC_ASYNC_IO 1000000 ${GKFS_MNTDIR}/mpi"
        #  ├─ NEK5000
        # self.app_call = "./nek5000"
        # self.app_dir = "/home/tarrafah/nhr-admire/shared/run_gkfs_marc"
        #  └─ Wacom++
        self.app_call = "./wacommplusplus"
        self.app_dir = "/lustre/project/nhr-admire/tarraf/wacommplusplus/build"

        # ****** pre and post app call ******
        # Application specific calls executed before the actual run. Executed as
        # > ${PRE_APP_CALL}
        # > cd self.app_dir && mpiexec ${some flags} ..${APP_CALL}
        # > ${POST_APP_CALL}
        # ├─ Nek5000
        if "nek" in self.app_call:
            if self.exclude_all:
                self.pre_app_call  = f"echo -e 'turbPipe\\n{self.app_dir}/input' > {self.app_dir}/SESSION.NAME"
                self.post_app_call = f"rm {self.app_dir}/input/*.f* || echo true"
            else:
                self.pre_app_call  = f"echo -e 'turbPipe\\n{self.gkfs_mntdir}' > {self.app_dir}/SESSION.NAME"
                self.post_app_call = ""
        # ├─ Wacom++
        elif "wacom" in self.app_call:
            if self.exclude_all:
                # in case a previous simulation fails
                self.pre_app_call = (
                    f"export OMP_NUM_THREADS={self.omp_threads}; ln -sf {self.app_dir}/wacomm.pfs.json {self.app_dir}/wacomm.json; "
                    f"cd {self.app_dir} && rm -rf input restart results processed output; cp -r stage-in/* . "
                )
                self.post_app_call = ""
            else:
                # modify wacomm.gkfs.json to include gkfs_mntdir
                self.pre_app_call = (
                    f"export OMP_NUM_THREADS={self.omp_threads}; ln -sf {self.app_dir}/wacomm.gkfs.json {self.app_dir}/wacomm.json; "
                                    )
                self.post_app_call = f"ln -sf {self.app_dir}/wacomm.pfs.json {self.app_dir}/wacomm.json"
        # └─ Other
        else:
            self.pre_app_call = ""
            self.post_app_call = ""

        # ? Stage in/out
        # ?##########################
        # ├─ Nek5000
        if "nek" in self.app_call:
            self.stage_in_path = f"{self.app_dir}/input"
            self.stage_out_path = "/lustre/project/nhr-admire/tarraf/stage-out"
        # ├─ Wacom++
        elif "wacom" in self.app_call:
            self.stage_in_path = f"{self.app_dir}/stage-in"
            self.stage_out_path = "/lustre/project/nhr-admire/tarraf/stage-out"
        # └─ Other
        else:
            self.stage_in_path = f"{self.app_dir}/stage-in"
            self.stage_out_path = "/lustre/project/nhr-admire/tarraf/stage-out"

        # ? Regex if needed
        # ?##########################
        self.regex_file = "/lustre/project/nhr-admire/shared/nek_regex4cargo.txt"
        # ├─ Nek5000
        if "nek" in self.app_call:
            self.regex_match = "^/[a-zA-Z0-9]*turbPipe0\\.f\\d+"
        # ├─ Wacom++
        elif "wacom" in self.app_call:
            self.regex_match = "^(\\/output|\\/results|\\/restart|\\/input)\\/[^\\/]+$"  # "^ocm3_d03_\\d+Z\d+\\.nc$"
        # └─ Other
        else:
            self.regex_match = ""

        # ? local machine settings
        # ?###############################
        if not self.cluster:
            self.install_location = "/d/github/JIT"
            self.regex_file = f"{self.install_location}/nek_regex4cargo.txt"

            self.ftio_bin_location = "/d/github/FTIO/.venv/bin"
            self.gkfs_daemon = f"{self.install_location}/iodeps/bin/gkfs_daemon"
            self.gkfs_intercept = (
                f"{self.install_location}/iodeps/lib/libgkfs_intercept.so"
            )
            self.gkfs_mntdir = "/tmp/jit/tarraf_gkfs_mountdir"
            self.gkfs_rootdir = "/tmp/jit/tarraf_gkfs_rootdir"
            self.gkfs_hostfile = f"{os.getcwd()}/gkfs_hosts.txt"
            self.gkfs_proxy = (
                f"{self.install_location}/gekkofs/build/src/proxy/gkfs_proxy"
            )
            self.gkfs_proxyfile = f"{self.install_location}/tarraf_gkfs_proxy.pid"
            self.cargo = f"{self.install_location}/cargo/build/src/cargo"
            self.cargo_cli = f"{self.install_location}/cargo/build/cli"

            # Nek5000
            self.app_dir = "/d/benchmark/Nek5000/turbPipe/run"
            self.app_call = "./nek5000"
            self.stage_in_path = "/d/benchmark/Nek5000/turbPipe/run/input"
            self.stage_out_path = "/tmp/output"
            if self.exclude_all:
                self.pre_app_call = "echo -e 'turbPipe\\n/d/benchmark/Nek5000/turbPipe/run/input' > /d/benchmark/Nek5000/turbPipe/run/SESSION.NAME"
                self.post_app_call = (
                    "rm /d/benchmark/Nek5000/turbPipe/run/input/*.f* || true"
                )
            else:
                self.pre_app_call = f"echo -e 'turbPipe\\n{self.gkfs_mntdir}' > /d/benchmark/Nek5000/turbPipe/run/SESSION.NAME"
                self.post_app_call = f"rm {self.stage_out_path}/*.f* || true"

            # self.stage_in_path = "/tmp/input"
            # self.stage_out_path = "/tmp/output"
