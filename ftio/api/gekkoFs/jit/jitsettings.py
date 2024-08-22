import os
import socket
from rich.console import Console

console = Console()


class JitSettings:
    def __init__(self) -> None:
        """sets the internal variables, don't modify this part.
        """

        # self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.log_dir = ""

        # Variable initialization
        self.cluster = False
        self.job_id = 0
        self.static_allocation = False

        self.ftio_node = ""
        self.single_node = ""
        self.app_nodes = 0
        self.all_nodes = ""
        self.app_nodes_command = ""
        self.ftio_node_command = ""
        self.single_node_command = ""

        self.log_dir = ""
        self.gekko_demon_log = ""
        self.gekko_demon_err = ""
        self.gekko_proxy_log = ""
        self.gekko_proxy_err = ""
        self.gekko_client_log = ""
        self.cargo_log = ""
        self.cargo_err = ""
        self.ftio_log = ""
        self.ftio_err = ""
        self.app_log = ""
        self.app_err = ""

        #exclude flags
        self.exclude_ftio = False
        self.exclude_cargo = False
        self.exclude_demon = False
        self.exclude_proxy = False
        self.exclude_all = False

        # pid of processes
        self.ftio_pid = 0
        self.gekko_demon_pid = 0
        self.gekko_proxy_pid = 0
        self.cargo_pid = 0
        self.log_speed = 0.1

        # parsed variables
        ###################
        self.address_ftio = "127.0.0.1"
        self.address_cargo = "127.0.0.1"
        self.port = "5555"
        self.nodes = 1
        self.procs = 128
        self.max_time = 30
        self.debug = True

        self.procs_demon = 0
        self.procs_proxy = 0
        self.procs_cargo = 0
        self.procs_app   = 0
        self.procs_ftio  = 0
        
        self.set_cluster_mode()
        self.set_default_procs()
        self.set_variables()

    def set_cluster_mode(self) -> None:
        """automatically identifies if it's a cluster or local machine
        """
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
        self.set_falgs()
        self.set_variables()

    def  set_default_procs(self) -> None:
    #default values for the procs in proc_list is not passed
        if self.cluster:
            self.procs_demon = self.procs
            self.procs_proxy = self.procs
            self.procs_ftio  = self.procs
        else:
            self.procs = 10
            self.procs_demon = 1
            self.procs_proxy = 1
            self.procs_ftio  = 1

        self.procs_cargo = 2
        self.procs_app = self.procs


    def set_falgs(self) -> None:
        """sets the flags in case exclude all is specified
        in the options passed
        """
        if self.exclude_all:
            self.exclude_ftio = True
            self.exclude_cargo = True
            self.exclude_demon = True
            self.exclude_proxy = True

        if not self.cluster:
            if self.nodes > 1:
                self.procs = self.nodes
                self.nodes = 1
                console.print(
                    f"[bold green]JIT [bold cyan]>> correcting nodes to {self.nodes} and processes to {self.procs} [/]"
                )

        if self.exclude_ftio:
            self.procs_ftio  = 0
        if self.exclude_cargo:
            self.procs_cargo = 0
        if self.exclude_demon:
            self.procs_demon = 0
        if self.exclude_proxy:
            self.procs_proxy = 0

    def set_log_dirs(self):
        self.gekko_demon_log = os.path.join(self.log_dir, "gekko_demon.log")
        self.gekko_demon_err = os.path.join(self.log_dir, "gekko_demon.err")
        self.gekko_proxy_log = os.path.join(self.log_dir, "gekko_proxy.log")
        self.gekko_proxy_err = os.path.join(self.log_dir, "gekko_proxy.err")
        self.gekko_client_log = os.path.join(self.log_dir, "gekko_client.log")
        self.cargo_log       = os.path.join(self.log_dir, "cargo.log")
        self.cargo_err       = os.path.join(self.log_dir, "cargo.err")
        self.ftio_log        = os.path.join(self.log_dir, "ftio.log")
        self.ftio_err        = os.path.join(self.log_dir, "ftio.err")
        self.app_log         = os.path.join(self.log_dir, "app.log")
        self.app_err        = os.path.join(self.log_dir, "app.err")

        
    #! only modify here
    def set_variables(self) -> None:
        """sets the path variables
        """
        # job allocation call
        # self.alloc_call_flags = "--overcommit --oversubscribe --partition parallel -A nhr-admire --job-name JIT --no-shell --exclude=cpu0082"
        self.alloc_call_flags = "--overcommit --oversubscribe --partition largemem -A nhr-admire --job-name JIT --no-shell --exclude=cpu0082,cpu0083"

        # ftio variables
        self.ftio_activate = "/lustre/project/nhr-admire/tarraf/FTIO/.venv/bin/activate"

        # gekko variables
        self.gkfs_demon = (
            "/lustre/project/nhr-admire/tarraf/deps/gekkofs_zmq_install/bin/gkfs_daemon"
        )
        self.gkfs_intercept = "/lustre/project/nhr-admire/tarraf/deps/gekkofs_zmq_install/lib64/libgkfs_intercept.so"
        self.gkfs_mntdir = "/dev/shm/tarraf_gkfs_mountdir"
        self.gkfs_rootdir = "/dev/shm/tarraf_gkfs_rootdir"
        self.gkfs_hostfile = "/lustre/project/nhr-admire/tarraf/gkfs_hosts.txt"
        self.gkfs_proxy = (
            "/lustre/project/nhr-admire/tarraf/gekkofs/build/src/proxy/gkfs_proxy"
        )
        self.gkfs_proxyfile = "/dev/shm/tarraf_gkfs_proxy.pid"

        # cargo variables
        self.cargo = "/lustre/project/nhr-admire/tarraf/cargo/build/src/cargo"
        self.cargo_cli = "/lustre/project/nhr-admire/tarraf/cargo/build/cli"
        self.cargo_server = "ofi+sockets://127.0.0.1:62000"

        # stage out variables
        self.stage_out_path = "/lustre/project/nhr-admire/tarraf/stage-out"
        self.regex_file = "/lustre/project/nhr-admire/shared/nek_regex4cargo.txt"
        self.regex_match = "^/[a-zA-Z0-9]*turbPipe0\\.f\\d+"

        # stage in variables
        self.stage_in_path = (
            "/lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/input"
        )

        # pre call
        # execute as ${PRECALL} mpiexec ${some flags} ..${APP_CALL}
        self.precall = (
            "cd /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs &&"
        )

        # pre and post app call
        # Application specific calls executed before the actual run. Executed as
        # ${PRE_APP_CALL}
        # ${PRECALL} mpiexec ${some flags} ..${APP_CALL}
        # ${POST_APP_CALL}
        if self.exclude_all:
            self.pre_app_call = "echo -e 'turbPipe\\n/lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/input' > /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/SESSION.NAME"
            self.post_app_call = "rm /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/input/*.f* || echo true"
        else:
            self.pre_app_call = f"echo -e 'turbPipe\\n{self.gkfs_mntdir}' > /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/SESSION.NAME"
            self.post_app_call = ""

        # app call
        # self.app="/lustre/project/nhr-admire/tarraf/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
        # self.app="/lustre/project/nhr-admire/tarraf/HACC-IO/HACC_ASYNC_IO 1000000 ${GKFS_MNTDIR}/mpi"
        self.app_call = "./nek5000"

        # install location
        if self.cluster:
            self.install_location = "/beegfs/home/Shared/admire/JIT"

        # local machine settings
        if not self.cluster:
            self.install_location = "/d/github/JIT"
            self.regex_file = f"{self.install_location}/nek_regex4cargo.txt"

            self.ftio_activate = "/d/github/FTIO/.venv/bin/activate"
            self.gkfs_demon = f"{self.install_location}/iodeps/bin/gkfs_daemon"
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
            self.stage_in_path = "/tmp/input"
            self.stage_out_path = "/tmp/output"

            # Nek5000
            self.precall = "cd /d/benchmark/Nek5000/turbPipe/run/ &&"
            self.app_call = "./nek5000"
            self.stage_in_path = "/d/benchmark/Nek5000/turbPipe/run/input"
            if self.exclude_all:
                self.pre_app_call = "echo -e 'turbPipe\\n/d/benchmark/Nek5000/turbPipe/run/input' > /d/benchmark/Nek5000/turbPipe/run/SESSION.NAME"
                self.post_app_call = "rm /d/benchmark/Nek5000/turbPipe/run/input/*.f* || true"
            else:
                self.pre_app_call = f"echo -e 'turbPipe\\n{self.gkfs_mntdir}' > /d/benchmark/Nek5000/turbPipe/run/SESSION.NAME"
                self.post_app_call = f"rm {self.stage_out_path}/*.f* || true"
