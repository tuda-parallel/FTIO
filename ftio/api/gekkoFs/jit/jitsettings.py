import os 
import socket 
from rich.console import Console
console = Console()




class JitSettings():
    def __init__(self):

        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.log_dir = ""

        # Variable initialization
        self.finish = False
        self.cluster = False
        self.jit_id = 0
        self.ftio_node = ""
        self.single_node = ""
        self.app_nodes = 0
        self.all_nodes = ""
        self.app_nodes_command = ""
        self.ftio_node_command = ""
        self.single_node_command = ""
        self.log_dir = ""
        self.app_time = ""
        self.stage_in_time = ""
        self.stage_out_time = ""
        self.exclude_ftio = False
        self.exclude_cargo = False
        self.exclude_demon = False
        self.exclude_proxy = False
        self.exclude_all = False
        self.ftio_pid = 0
        self.gekko_demon_pid = 0
        self.gekko_proxy_pid = 0
        self.cargo_pid = 0

        # parsed variables
        ###################
        self.address_ftio = "127.0.0.1"
        self.address_cargo = "127.0.0.1"
        self.port = "5555"
        self.nodes = 2
        self.procs = 128
        self.max_time = 30
        self.debug=True

        self.set_cluster_mode()
        self.set_variables()
        
    def set_cluster_mode(self):
        hostname = socket.gethostname()
        if "cpu" in hostname or "mogon" in hostname:
            self.cluster = True
            if "mogon" in hostname:
                console.print("[bold red] Execute this script on CPU nodes\n mpiexec still has some bugs[/]")

        console.print(f"[bold green]JIT >> CLUSTER MODE: {self.cluster}[/]")

    def update(self) -> None:
        self.set_falgs()
        self.set_variables()

    def set_falgs(self):
        if self.exclude_all:
            self.exclude_ftio = True
            self.exclude_cargo = True
            self.exclude_demon = True
            self.exclude_proxy = True

    #! only modify here
    def set_variables(self):
        # job allocation call
        self.alloc_call_flags = "--overcommit --oversubscribe --partition parallel -A nhr-admire --job-name JIT --no-shell --exclude=cpu0082"
        # self.alloc_call_flags = "--overcommit --oversubscribe --partition largemem -A nhr-admire --job-name JIT --no-shell --exclude=cpu0082"

        # ftio variables
        self.ftio_activate = '/lustre/project/nhr-admire/tarraf/FTIO/.venv/bin/activate'

        # gekko variables
        self.gkfs_demon = '/lustre/project/nhr-admire/vef/deps/gekkofs_zmq_install/bin/gkfs_daemon'
        self.gkfs_intercept = '/lustre/project/nhr-admire/vef/deps/gekkofs_zmq_install/lib64/libgkfs_intercept.so'
        self.gkfs_mntdir = '/dev/shm/tarraf_gkfs_mountdir'
        self.gkfs_rootdir = '/dev/shm/tarraf_gkfs_rootdir'
        self.gkfs_hostfile = '/lustre/project/nhr-admire/tarraf/gkfs_hosts.txt'
        self.gkfs_proxy = '/lustre/project/nhr-admire/vef/gekkofs/build/src/proxy/gkfs_proxy'
        self.gkfs_proxyfile = '/dev/shm/tarraf_gkfs_proxy.pid'

        # cargo variables
        self.cargo = '/lustre/project/nhr-admire/vef/cargo/build/src/cargo'
        self.cargo_cli = '/lustre/project/nhr-admire/vef/cargo/build/cli'
        self.cargo_server = 'ofi+sockets://127.0.0.1:62000'

        # stage out variables
        self.stage_out_path = '/lustre/project/nhr-admire/tarraf/stage-out'
        self.regex_file = '/lustre/project/nhr-admire/shared/nek_regex4cargo.txt'
        self.regex_match = '^/[a-z0-9]*turbpipe0\\.f\\d+'

        # stage in variables
        self.stage_in_path = '/lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/input'

        # pre call
        # execute as ${PRECALL} mpiexec ${some flags} ..${APP_CALL}
        self.precall="cd /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs &&"

        # pre and post app call
        # Application specific calls executed before the actual run. Executed as
        # ${PRE_APP_CALL}
        # ${PRECALL} mpiexec ${some flags} ..${APP_CALL}
        # ${POST_APP_CALL}
        if self.exclude_all:
            self.pre_app_call = "echo -e 'turbpipe\\n/lustre/project/nhr-admire/tarraf/admire/turbpipe/run_gkfs/input' > /lustre/project/nhr-admire/tarraf/admire/turbpipe/run_gkfs/SESSION.NAME"
            self.post_app_call = "rm /lustre/project/nhr-admire/tarraf/admire/turbpipe/run_gkfs/input/*.f*"
        else:
            self.pre_app_call = f"echo -e 'turbpipe\\n{self.gkfs_mntdir}' > /lustre/project/nhr-admire/tarraf/admire/turbpipe/run_gkfs/SESSION.NAME"
            self.post_app_call = ""

        # app call
        #self.app="/lustre/project/nhr-admire/tarraf/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
        #self.app="/lustre/project/nhr-admire/tarraf/HACC-IO/HACC_ASYNC_IO 1000000 ${GKFS_MNTDIR}/mpi"
        self.app_call = "./nek5000"

        # install location
        if self.cluster:
            self.install_location = '/beegfs/home/Shared/admire/JIT'

        # local machine settings
        if not self.cluster:
            self.install_location = '/d/github/JIT'
            self.regex_file = f"{self.install_location}/nek_regex4cargo.txt"
            
            self.ftio_activate = "/d/github/FTIO/.venv/bin/activate"
            self.gkfs_demon = f"{self.install_location}/iodeps/bin/gkfs_daemon"
            self.gkfs_intercept = f"{self.install_location}/iodeps/lib/libgkfs_intercept.so"
            self.gkfs_mntdir = "/tmp/jit/tarraf_gkfs_mountdir"
            self.gkfs_rootdir = "/tmp/jit/tarraf_gkfs_rootdir"
            self.gkfs_hostfile = f"{os.getcwd()}/gkfs_hosts.txt"
            self.gkfs_proxy = f"{self.install_location}/gekkofs/build/src/proxy/gkfs_proxy"
            self.gkfs_proxyfile = f"{self.install_location}/tarraf_gkfs_proxy.pid"
            self.cargo = f"{self.install_location}/cargo/build/src/cargo"
            self.cargo_cli = f"{self.install_location}/cargo/build/cli"
            self.stage_in_path = "/tmp/input"
            self.stage_out_path = "/tmp/output"
            
            # Nek5000
            self.precall = "cd /d/benchmark/Nek5000/turbPipe/run/ &&"
            self.app_call = "./nek5000"
            self.stage_in_path="/d/benchmark/Nek5000/turbPipe/run/input"
            if self.exclude_all:
                self.pre_app_call = "echo -e 'turbPipe\\n/d/benchmark/Nek5000/turbPipe/run/input' > /d/benchmark/Nek5000/turbPipe/run/SESSION.NAME"
                self.post_app_call = "rm /d/benchmark/Nek5000/turbPipe/run/input/*.f*"
            else:
                self.pre_app_call = f"echo -e 'turbPipe\\n{self.gkfs_mntdir}' > /d/benchmark/Nek5000/turbPipe/run/SESSION.NAME"
                self.post_app_call = f"rm {self.stage_out_path}/*.f*"