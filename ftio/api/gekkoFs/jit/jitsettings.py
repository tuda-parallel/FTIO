"""
JIT Settings 

Author: Ahmad Tarraf  
Copyright (c) 2025 TU Darmstadt, Germany  
Date: Aug 2024

Licensed under the BSD 3-Clause License. 
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import os
import re
import socket
import numpy as np
from rich.console import Console

console = Console()


class JitSettings:
    def __init__(self) -> None:
        """sets the internal variables, don't modify this part (except flags if needed).
        only Adjust the paths in the function set_variables
        """

        # app
        ##############
        # can be controlled through command line arguments see jit -h)
        self.app = ""
        
        # flags
        ##############
        self.set_tasks_affinity = True  # required for ls and cp
        self.cargo_mode = "posix"  # "parallel" or "posix"
        self.debug_lvl = 0
        self.verbose = True
        self.verbose_error = True
        self.node_local = True  # execute in node local space or memory
        self.env_var = {}
        self.log_speed = 0.1 # how fast to read the log
        

        # Variable initialization (don't change)
        ################
        self.dry_run = False
        self.log_suffix = "DPCF"
        self.run_dir = ""
        self.dir = ""
        self.cluster = False
        self.ignore_mtime = False
        self.parallel_move = False
        self.lock_generator = False
        self.lock_consumer = False
        self.adaptive = "cancel"
        self.job_id = 0
        self.static_allocation = False
        self.ftio_node = ""
        self.single_node = ""
        self.app_nodes = 0
        self.all_nodes = 0
        self.app_nodes_command = ""
        self.ftio_node_command = ""
        self.single_node_command = ""
        self.alloc_call_flags = ""
        self.job_name = ""
        self.ftio_bin_location = ""
        self.gkfs_hostfile = ""
        self.gkfs_proxyfile = ""
        self.mpi_hostfile = ""
        self.parsed_gkfs_daemon = ""
        self.parsed_gkfs_intercept = ""
        
        self.log_dir = ""
        self.gkfs_daemon_log = ""
        self.gkfs_daemon_err = ""
        self.gkfs_proxy_log = ""
        self.gkfs_proxy_err = ""
        self.gkfs_client_log = ""
        self.cargo_log = ""
        self.cargo_err = ""
        self.ftio_log = ""
        self.ftio_err = ""
        self.app_log = ""
        self.app_err = ""

        # exclude flags
        ################
        self.exclude_ftio = False
        self.exclude_cargo = False
        self.exclude_daemon = False
        self.exclude_proxy = True
        self.exclude_all = False

        # pid of processes
        ################
        self.ftio_pid = 0
        self.gkfs_daemon_pid = 0
        self.gkfs_proxy_pid = 0
        self.cargo_pid = 0
        self.app_pid = 0

        # parsed variables
        ###################
        self.address_ftio = "127.0.0.1"
        self.port_ftio = "5555" # port between ftio and gkfs
        self.address_cargo = "127.0.0.1"
        self.port_cargo = "62000" #port between cargo and ftio
        
        self.nodes = 1
        self.max_time = 30
        self.ftio_args = "-m write -v --freq -1" #10 -w data -v "
        self.gkfs_daemon_protocol = (
            "ofi+verbs"  # "ofi+verbs" #"ofi+sockets"  or "ofi+verbs"
        )
        self.skip_confirm = False
        self.use_mpirun = False
        self.gkfs_use_syscall = False
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
        self.cmd_call = ""
        

        self.set_cluster_mode()
        self.set_default_procs()
        self.set_variables()

    def __str__(self) -> str:
        """returns the settings in a readable format
        """
        return str(self.to_dict())

        
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
        """updates settings after command line arguments gave been parsed
        """
        # Dry run settings
        if self.dry_run:
            new_name = "Dry_" + self.job_name
            self.alloc_call_flags = self.alloc_call_flags.replace(
                self.job_name, new_name
            )
            self.job_name = new_name

        # Gekko settings
        if self.gkfs_use_syscall:
            # already correct
            pass 
        else:
            self.gkfs_intercept = self.gkfs_intercept.replace("_intercept.so", "_libc_intercept.so")

    def set_absolute_path(self) -> None:
        self.run_dir = os.path.expanduser(self.run_dir)
        self.dir = os.path.expanduser(os.getcwd())
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
            self.procs = os.cpu_count()/2 if os.cpu_count() else 4
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

    def set_mpi_host_file(self,job_id=None):
        if job_id:
            self.mpi_hostfile = f"{self.dir}/mpi_hostfile_{self.job_id}"
        else:
            self.mpi_hostfile = f"{self.dir}/mpi_hostfile"



            
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
            self.log_suffix = self.log_suffix.replace("D", "")
        if self.exclude_proxy:
            self.procs_proxy = 0
            self.log_suffix = self.log_suffix.replace("P", "")
        if self.exclude_cargo:
            self.procs_cargo = 0
            self.log_suffix = self.log_suffix.replace("C", "")
        if self.exclude_ftio:
            self.procs_ftio = 0
            self.log_suffix = self.log_suffix.replace("F", "")

        if self.set_tasks_affinity:
            self.task_set_0 = f"taskset -c 0-{np.floor(self.procs/2)-1:.0f}"
            if self.procs - np.floor(self.procs / 2) >= self.procs_app:
                self.task_set_1 = (
                    f"taskset -c {np.ceil(self.procs/2):.0f}-{self.procs-1:.0f}"
                )

    def set_log_dirs(self):
        self.gkfs_daemon_log = os.path.join(self.log_dir, "gekko_daemon.log")
        self.gkfs_daemon_err = os.path.join(self.log_dir, "gekko_daemon.err")
        self.gkfs_proxy_log = os.path.join(self.log_dir, "gekko_proxy.log")
        self.gkfs_proxy_err = os.path.join(self.log_dir, "gekko_proxy.err")
        self.gkfs_client_log = os.path.join(self.log_dir, "gekko_client.log")
        self.cargo_log = os.path.join(self.log_dir, "cargo.log")
        self.cargo_err = os.path.join(self.log_dir, "cargo.err")
        self.ftio_log = os.path.join(self.log_dir, "ftio.log")
        self.ftio_err = os.path.join(self.log_dir, "ftio.err")
        self.app_log = os.path.join(self.log_dir, "app.log")
        self.app_err = os.path.join(self.log_dir, "app.err")

    def to_dict(self):  # -> dict[str, Any]:
        # Define a list of attribute names to be promoted to top-level keys
        top_level_keys = [
            'log_suffix',  # This will be renamed to 'mode'
            'app',         # This will be renamed to 'app name'
            'nodes',
            'procs',
            'procs_app',
            'procs_ftio',
            'procs_daemon',
            'procs_proxy',
            'procs_cargo',
            'omp_threads',
            'task_set_0',
            'task_set_1',
        ]

        # Initialize the result dictionary with top-level keys in the desired order
        result = {}

        # Iterate over the top-level keys and add them to the result dictionary if they exist
        for key in top_level_keys:
            value = getattr(self, key, None)
            if value is not None:
                if key == 'log_suffix':
                    result['mode'] = value
                elif key == 'app':
                    result['app name'] = value
                else:
                    result[key.replace('_', ' ')] = value

        # Add the 'settings' dictionary at the end
        result['settings'] = {}

        # Iterate over all instance attributes
        for key, value in self.__dict__.items():
            # Skip keys that have already been added as top-level keys
            if key in top_level_keys:
                continue
            # Replace underscores with spaces in the key for settings
            new_key = key.replace('_', ' ')
            result['settings'][new_key] = value

        # Handle specific conditions for certain fields
        if self.exclude_daemon:
            result['settings']["gkfs mntdir"] = ""
            result['settings']["gkfs rootdir"] = ""

        return result


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
        # self.alloc_call_flags = f"--overcommit --oversubscribe --partition largemem -A nhr-admire --job-name {self.job_name} --no-shell --exclude=cpu0081,cpu0082,cpu0083,cpu0084,cpu0401"
        self.alloc_call_flags = f"--overcommit --oversubscribe --partition parallel -A nhr-admire --job-name {self.job_name} --no-shell --exclude=cpu0081,cpu0082,cpu0083,cpu0084,cpu0085,cpu0086,cpu0087,cpu0088,cpu0401"

        # ? Tools
        # ?##########################
        # ****** ftio variables ******
        self.ftio_bin_location = "/lustre/project/nhr-admire/tarraf/FTIO/.venv/bin"

        # ****** gkfs variables ******
        self.gkfs_deps = "/lustre/project/nhr-admire/tarraf/deps"  # _gcc12_2"
        if  self.parsed_gkfs_daemon:
            self.gkfs_daemon = self.parsed_gkfs_daemon
        else:
            self.gkfs_daemon = f"{self.gkfs_deps}/gekkofs_zmq_install/bin/gkfs_daemon"

        if  self.parsed_gkfs_intercept:
            self.gkfs_intercept = self.parsed_gkfs_intercept
        else:
            self.gkfs_intercept =  f"{self.gkfs_deps}/gekkofs_zmq_install/lib64/libgkfs_intercept.so" 

        self.gkfs_mntdir = "/dev/shm/tarraf_gkfs_mountdir"
        self.gkfs_rootdir = "/dev/shm/tarraf_gkfs_rootdir"
        self.gkfs_hostfile = "/lustre/project/nhr-admire/tarraf/gkfs_hosts.txt"
        self.gkfs_proxy =  "/lustre/project/nhr-admire/tarraf/gekkofs/build/src/proxy/gkfs_proxy"
        self.gkfs_proxyfile = "/dev/shm/tarraf_gkfs_proxy.pid"
        self.update_files_with_gkfs_mntdir =[]

        # ****** cargo variables ******
        self.cargo_bin = f"{self.gkfs_deps}/gekkofs_zmq_install/bin"  # "/lustre/project/nhr-admire/tarraf/cargo/build/cli"

        # ? APP settings
        # ?##########################
        # ****** app call ******
        #  ├─ IOR
        if "ior" in self.app:
            self.app_call = "/lustre/project/nhr-admire/tarraf/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
        #  ├─ HACCIO
        elif "hacc" in self.app:
            self.app_call ="/lustre/project/nhr-admire/tarraf/HACC-IO/HACC_ASYNC_IO 1000000 ${GKFS_MNTDIR}/mpi"
        # ├─ NEK5000 --> change gkfs_daemon_protocol to socket
        elif "nek" in self.app:
            self.app_call = "./nek5000"
            self.run_dir = "/home/tarrafah/nhr-admire/shared/run_gkfs_marc"
            self.app_flags = ""
        #  ├─ Wacom++ --> change wacom.json if needed
        elif "wacom" in self.app:
            self.app_call = "./wacommplusplus"
            # self.run_dir = "/lustre/project/nhr-admire/tarraf/wacommplusplus/build"
            # self.run_dir = "/lustre/project/nhr-admire/tarraf/wacommplusplus/roms"
            self.run_dir = "/lustre/project/nhr-admire/tarraf/wacommplusplus/build_new"
            if not self.app_flags: #default value if app_flags is not set
                self.app_flags = ""
        #  ├─ LAMMPS 
        elif "lammps" in self.app:
            self.app_call = "/lustre/project/nhr-admire/shared/mylammps/build/lmp"
            self.run_dir = f"{self.gkfs_mntdir}"
            self.app_flags = "-in in.spce.hex"
        #  ├─ DLIO 
        elif "dlio" in self.app:
            self.app_call = "dlio_benchmark"
            self.run_dir = "."
            # workload = " workload=bert " 
            # workload = " workload=bert_small " 
            # workload = " workload=unet3d_my_a100 "        
            # workload = " workload=resnet50_my_a100 "        
            # workload = " workload=llama_my_7b_zero3 "  
            workload = " workload=resnet50_my_a100_pytorch "    
            
            self.app_flags = (
                f"{workload} "
                f"++workload.workflow.generate_data=True ++workload.workflow.train=True ++workload.workflow.checkpoint=True " #++workload.workflow.evaluation=True "
                f"++workload.dataset.data_folder={self.run_dir}/data/jit ++workload.checkpoint.checkpoint_folder={self.run_dir}/checkpoints/jit "  
                f"++workload.output.output_folder={self.run_dir}/hydra_log/jit "
            )
        #  └─ S3D-IO
        elif "s3d" in self.app:
            self.app_call = "/lustre/project/nhr-admire/shared/S3D-IO/s3d_io.x"
            self.run_dir = "."
            if not self.app_flags: #default value if app_flags is not set
                self.app_flags = "600 600 600 6 6 6 0 F ."

        else:
            self.app_call = ""
            self.run_dir = ""
            self.app_flags = ""
        # ? Pre and post app settings
        # ?##########################
        # Application specific calls executed before the actual run. Executed as
        # > ${PRE_APP_CALL}
        # > cd self.run_dir && mpiexec ${some flags} ..${APP_CALL}
        # > ${POST_APP_CALL}
        # ├─ dlio
        if "dlio" in self.app:
            if self.exclude_daemon:
                # self.pre_app_call = f"mpirun -np 8 dlio_benchmark {self.app_flags} ++workload.workflow.generate_data=True ++workload.workflow.train=False"
                self.pre_app_call  = ""
                self.post_app_call = ""
            else:
                # self.run_dir = self.gkfs_mntdir #? don't enable this flag, as the executing node doesn't have this folder
                self.app_flags = (
                    f"{workload} "
                    f"++workload.workflow.generate_data=True ++workload.workflow.train=True ++workload.workflow.checkpoint=True " #++workload.workflow.evaluation=True "
                    f"++workload.dataset.data_folder={self.gkfs_mntdir}/data/jit ++workload.checkpoint.checkpoint_folder={self.gkfs_mntdir}/checkpoints/jit " 
                    f"++workload.output.output_folder={self.gkfs_mntdir}/hydra_log/jit "
                    # ++workload.output.log_file={self.gkfs_mntdir}/hydra_log/unet3d"# ++workload.dataset.num_files_train=16"
                )
                self.pre_app_call  = ""
                self.post_app_call = ""
        # ├─ Nek5000
        elif "nek" in self.app:
            if self.exclude_daemon:
                self.pre_app_call = f"echo -e 'turbPipe\\n{self.run_dir}/input' > {self.run_dir}/SESSION.NAME"
                self.post_app_call = f"rm {self.run_dir}/input/*.f* || echo true"
            else:
                self.pre_app_call = f"echo -e 'turbPipe\\n{self.gkfs_mntdir}' > {self.run_dir}/SESSION.NAME"
                self.post_app_call = ""
        # ├─ Wacom++
        elif "wacom" in self.app:
            if self.exclude_daemon:
                # in case a previous simulation fails
                self.pre_app_call = (
                    f"export OMP_NUM_THREADS={self.omp_threads}; ln -sf {self.run_dir}/wacomm.pfs.json {self.run_dir}/wacomm.json; "
                    f"cd {self.run_dir} && rm -rf input restart results processed output; cp -r stage-in/*  {self.run_dir} "
                )
                self.post_app_call = ""
            else:
                # modify wacomm.gkfs.json to include gkfs_mntdir
                self.update_files_with_gkfs_mntdir = [f"{self.run_dir}/wacomm.gkfs.json"]
                self.pre_app_call = (
                    f"export OMP_NUM_THREADS={self.omp_threads}; ln -sf {self.run_dir}/wacomm.gkfs.json {self.run_dir}/wacomm.json; "
                    )
                self.post_app_call = (
                    f"ln -sf {self.run_dir}/wacomm.pfs.json {self.run_dir}/wacomm.json"
                )
        # ├─ S3D-IO
        elif "s3d" in self.app:
            self.pre_app_call = ""
            self.post_app_call = ""
            if not self.exclude_daemon:
                self.app_flags = self.app_flags.replace('.', f"{self.gkfs_mntdir}")
        else:
            self.pre_app_call = ""
            self.post_app_call = ""

        # ? Stage in/out
        # ?##########################
        # ├─ Nek5000
        if "nek" in self.app:
            self.stage_in_path = f"{self.run_dir}/input"
            self.stage_out_path = "/lustre/project/nhr-admire/tarraf/stage-out"
        # ├─ Wacom++
        elif "wacom" in self.app:
            self.stage_in_path = f"{self.run_dir}/stage-in"
            self.stage_out_path = "/lustre/project/nhr-admire/tarraf/stage-out"
        # ├─ DLIO
        elif "dlio" in self.app:
            self.stage_in_path =  "/lustre/project/nhr-admire/tarraf/stage-in"
            self.stage_out_path = "/lustre/project/nhr-admire/tarraf/stage-out"
        # ├─ LAMMPS
        elif "lammps" in self.app:
            self.stage_in_path = "/lustre/project/nhr-admire/shared/mylammps/examples/HEAT"
            self.stage_out_path = "/lustre/project/nhr-admire/tarraf/stage-out"
        # └─ Other
        else:
            self.stage_in_path =  "/lustre/project/nhr-admire/tarraf/stage-in"
            self.stage_out_path = "/lustre/project/nhr-admire/tarraf/stage-out"

        # ? Regex relevant files (move matches out and in)
        # ?##########################
        self.regex_file = "/lustre/project/nhr-admire/shared/nek_regex4cargo.txt"
        # ├─ Nek5000
        if "nek" in self.app_call:
            self.regex_flush_match = ".*/[a-zA-Z0-9]*turbPipe0\\.f\\d+"
            self.regex_stage_out_match = ".*/[a-zA-Z0-9]*turbPipe0\\.f\\d+" #".*"
        # ├─ Wacom++
        elif "wacom" in self.app_call:
            self.regex_flush_match = ".*/(history|restart|output)/.*\\.(nc|json)$"
            # self.regex_flush_match = ".*/output/.*\\.nc$"
            # self.regex_stage_out_match = ".*"
            self.regex_stage_out_match = ".*/(history|restart|output)/.*\\.(nc|json)$"
        # ├─ DLIO
        elif "dlio" in self.app_call:
            self.regex_flush_match = ".*/(checkpoints)/jit/.*\\.pt$"
            self.regex_stage_out_match = ".*/(checkpoints)/jit/.*\\.pt$"
        # ├─ LAMMPS
        elif "lmp" in self.app_call:
            self.regex_flush_match = ""
            self.regex_stage_out_match = ".*"
        # ├─ S3D-IO
        elif "s3d" in self.app_call:
            self.regex_flush_match = ".*/pressure_wave_test\\..*\\.field\\.nc$"
            self.regex_stage_out_match = ".*"
        # └─ Other
        else:
            self.regex_flush_match = ""
            self.regex_stage_out_match = ".*"

        self.regex_match = self.regex_flush_match 
        self.env_var = {
            "CARGO_REGEX": self.regex_file
                        }
        
        # With GENERATOR (app): At open/create we create an extra .lockgekko file with size = number of opens to that file (it is distributed). We decrease and delete the file on close
        # with CONSUMER (Cargo): At Open we wait until (40 seconds~) for the lock file to dissapear. No modifications needed on the client, it is transparent.
        if self.lock_generator and not self.exclude_daemon:
            self.env_var["LIBGKFS_PROTECT_FILES_GENERATOR"]="1" #app, i.e., Gekko
        # else:
        #     self.env_var["LIBGKFS_PROTECT_FILES_GENERATOR"]="0"

        if self.lock_consumer and not self.exclude_cargo:
            self.env_var["LIBGKFS_PROTECT_FILES_CONSUMER"]="1" #Cargo
        # else:
        #     self.env_var["LIBGKFS_PROTECT_FILES_CONSUMER"]="0"


        # ? local machine settings
        # ?###############################
        if not self.cluster:
            self.gkfs_daemon_protocol ="ofi+sockets" #"ofi+tcp"
            self.install_location = "/d/github/JIT"
            self.ftio_bin_location = "/d/github/FTIO/.venv/bin"
            if  self.parsed_gkfs_daemon:
                self.gkfs_daemon = self.parsed_gkfs_daemon
            else:
                self.gkfs_daemon = f"{self.install_location}/iodeps/bin/gkfs_daemon"

            if  self.parsed_gkfs_intercept:
                self.gkfs_intercept = self.parsed_gkfs_intercept
            else:
                self.gkfs_intercept =  f"{self.install_location}/iodeps/lib/libgkfs_intercept.so" 
            
            self.gkfs_mntdir = "/tmp/jit/tarraf_gkfs_mountdir"
            self.gkfs_rootdir = "/tmp/jit/tarraf_gkfs_rootdir"
            self.gkfs_hostfile = f"{os.getcwd()}/gkfs_hosts.txt"
            self.gkfs_proxy = f"{self.install_location}/gekkofs/build/src/proxy/gkfs_proxy"
            self.gkfs_proxyfile = f"{self.install_location}/tarraf_gkfs_proxy.pid"
            self.cargo_bin = f"{self.install_location}/iodeps/bin"

            self.regex_file = "/tmp/jit/nek_regex4cargo.txt"
            self.env_var = {"CARGO_REGEX": self.regex_file}

            self.stage_in_path = "/tmp/input"
            self.stage_out_path = "/tmp/output"

            # Create the folder if it doesn't exist
            os.makedirs(self.stage_in_path, exist_ok=True)
            os.makedirs(self.stage_out_path, exist_ok=True)
            with open(os.path.join(self.stage_in_path, 'test.txt'), 'w') as f:
                pass
            
            if "dlio" in self.app:                
                self.stage_in_path = "/d/github/dlio_benchmark/data"
                # generate data with
                if self.exclude_daemon:
                    self.app_flags = (
                    f"{workload} "
                    f"++workload.workflow.generate_data=False ++workload.workflow.train=True ++workload.workflow.checkpoint=True " #++workload.workflow.evaluation=True "
                    f"++workload.dataset.data_folder={self.run_dir}/data/jit ++workload.checkpoint.checkpoint_folder={self.run_dir}/checkpoints/jit " 
                    f"++workload.output.output_folder={self.run_dir}/hydra_log/jit "
                    )
                    self.pre_app_call = (
                            f"mpirun -np 8 dlio_benchmark "
                            f"{workload} "
                            f"++workload.workflow.generate_data=True ++workload.workflow.train=False ++workload.workflow.checkpoint=True " #++workload.workflow.evaluation=True "
                            f"++workload.dataset.data_folder={self.run_dir}/data/jit ++workload.checkpoint.checkpoint_folder={self.run_dir}/checkpoints/jit " 
                            f"++workload.output.output_folder={self.run_dir}/hydra_log/jit "
                    )
                    self.post_app_call = ""
                else:
                    self.app_flags = (
                    f"{workload} "
                    f"++workload.workflow.generate_data=False ++workload.workflow.train=True ++workload.workflow.checkpoint=False " #++workload.workflow.evaluation=True "
                    f"++workload.dataset.data_folder={self.gkfs_mntdir}/data/jit ++workload.checkpoint.checkpoint_folder={self.gkfs_mntdir}/checkpoints/jit " 
                    f"++workload.output.output_folder={self.gkfs_mntdir}/hydra_log/jit "
                    )
                    self.pre_app_call = [
                        # f"cd {self.gkfs_mntdir}",
                        (
                            f"mpirun -np 8 dlio_benchmark "
                            f"{workload} "
                            f"++workload.workflow.generate_data=True ++workload.workflow.train=False ++workload.workflow.checkpoint=True " #++workload.workflow.evaluation=True "
                            f"++workload.dataset.data_folder={self.gkfs_mntdir}/data/jit ++workload.checkpoint.checkpoint_folder={self.gkfs_mntdir}/checkpoints/jit " 
                            f"++workload.output.output_folder={self.gkfs_mntdir}/hydra_log/jit "
                    )
                    ]
                    self.post_app_call = ""
                # ├─ Nek5000
            elif "nek" in self.app:
                self.run_dir = "/d/benchmark/Nek5000/turbPipe/run"
                self.stage_in_path = "/d/benchmark/Nek5000/turbPipe/run/input"
                if self.exclude_daemon:
                    self.pre_app_call = "echo -e 'turbPipe\\n/d/benchmark/Nek5000/turbPipe/run/input' > /d/benchmark/Nek5000/turbPipe/run/SESSION.NAME"
                    self.post_app_call = (
                        "rm /d/benchmark/Nek5000/turbPipe/run/input/*.f* || true"
                    )
                else:
                    self.pre_app_call = f"echo -e 'turbPipe\\n{self.gkfs_mntdir}' > /d/benchmark/Nek5000/turbPipe/run/SESSION.NAME"
                    self.post_app_call = f"rm {self.stage_out_path}/*.f* || true"
            elif "s3d" in self.app:
                self.app_call = "/d/benchmark/S3D-IO/s3d_io.x"
                # execute "mkdir -p /d/benchmark/S3D-IO/input && touch /d/benchmark/S3D-IO/input/test"
                self.stage_in_path = "/tmp/input"
                if not self.exclude_daemon:
                    self.app_flags =  re.sub(r"/[^\s]+", self.gkfs_mntdir, self.app_flags)
