#! /bin/bash
# Contains all functions used


# Function to check if PORT is in use
function is_port_in_use() {
	local port_number=$1
	port_output=$(netstat -tlpn | grep ":$port_number ")
	if [[ ! -z "$port_output" ]]; then
		# Port is in use
		echo -e "${RED}Error: Port $port_number is already in use...${BLACK}"
		return 0 # true, port is in use
	else
		# Port is free
		echo -e "${BLUE}Port $port_number is available.${BLACK}"
		return 1 # false, port is free
	fi
}

function check_port(){

# Check if PORT is available
if is_port_in_use $PORT; then
	echo -e "${RED}Error: Port $PORT is already in use on $ADDRESS. Terminating existing process...${BLACK}"

	# Use ss command for potentially more reliable process identification (uncomment)
	# process_id=$(ss -tlpn | grep :"$PORT " | awk '{print $NF}')

	# Use netstat if ss is unavailable (uncomment)
	process_id=$(netstat -tlpn | grep :"$PORT " | awk '{print $7}')

	if [[ ! -z "$process_id" ]]; then
		echo -e "${YELLOW}Terminating process with PID: $process_id${BLACK}"
		kill "${process_id%/*}" && echo -e "${GREEN}Using $PORT on $ADDRESS.${BLACK}"
		return 0
	else
		echo -e "${RED}Failed to identify process ID for PORT $PORT.${BLACK}"
	fi
	exit 1
else
	echo -e "${GREEN}Using $PORT on $ADDRESS.${BLACK}"
fi
}


function allocate(){
	
	if [ "$CLUSTER" = true ]; then
		salloc -N $NODES -t ${MAX_TIME} --overcommit --oversubscribe --partition parallel -A nhr-admire
	fi
}

# Start the Server
function start_geko() {
	echo -e "${GREEN}####### GKFS DEOMON started ${BLACK}"
	
	if [ "$CLUSTER" = true ]; then
		srun --disable-status -N 1 --ntasks=1 --cpus-per-task=128 \
		--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
		${GKFS_DEMON}  \
		-r /dev/shm/tarraf_gkfs_rootdir \
		-m /dev/shm/tarraf_gkfs_mountdir \
		-H ${GKFS_HOSTFILE}  -c -l ib0
	else
		# Geko Demon call
		GKFS_DAEMON_LOG_PATH=/tmp/gkfs_daemon.log \
			GKFS_DAEMON_LOG_LEVEL=info \
			${GKFS_DEMON} \
			-r /tmp/gkfs_rootdir \
			-m /tmp/gkfs_mountdir \
			-c --auto-sm \
			-H ${GKFS_HOSTFILE} 
	fi
}

# Application call
function start_application() {
	echo -e "${CYAN}Executing Application ${BLACK}"
	
	# application with Geko LD_PRELOAD
	if [ "$CLUSTER" = true ]; then
		srun --disable-status -N $NODES --ntasks=1 --cpus-per-task=128 \
			--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
			-x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} \
			-x LIBGKFS_LOG=none \
			-x LIBGKFS_ENABLE_METRICS=on \
			-x LIBGKFS_METRICS_IP_PORT=${ADDRESS}:${PORT} \
			-x LD_PRELOAD=${GKFS_INERCEPT} \
			${APP_CALL}
	else
		mpiexec -np $NODES --oversubscribe \
			-x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} \
			-x LIBGKFS_LOG=none \
			-x LIBGKFS_ENABLE_METRICS=on \
			-x LIBGKFS_METRICS_IP_PORT=${ADDRESS}:${PORT} \
			-x LD_PRELOAD=${GKFS_INERCEPT} \
			${APP_CALL}
		echo -e "${CYAN}Application finished ${BLACK}\n"
	fi 
	FINISH=true
}

function start_cargo() {
	echo -e "${GREEN}####### Starting Cargo ${BLACK}"
	
	if [ "$CLUSTER" = true ]; then
		srun --disable-status -N 1 --ntasks=1 --cpus-per-task=128 \
			--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
			--map-by node \
			-x LIBGKFS_HOS_FILE=${GKFS_HOSTFILE} \
			--hostfile /lustre/project/nhr-admire/tarraf/hostfile \
			${CARGI} --listen \
			ofi+sockets://127.0.0.1:62000 \
	else
		mpiexec -np 2 --oversubscribe \
			--map-by node \
			-x LIBGKFS_HOS_FILE=${GKFS_HOSTFILE} \
			--hostfile /lustre/project/nhr-admire/tarraf/hostfile \
			${CARGI} --listen \
			ofi+sockets://127.0.0.1:62000 \
			>> ./cargo_${NODES}.txt
	fi
}


function start_ftio() {
	echo -e "${GREEN}####### Starting FTIO ${BLACK}\n"

	if [ "$CLUSTER" = true ]; then
		source ${FTIO_ACTIVATE}
		srun --disable-status -N 1 --ntasks=1 --cpus-per-task=128 \
		--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
		predictor_gekko  --zmq_address ${ADDRESS} --zmq_port ${PORT}
		# Change CARGO path in predictor_gekko_zmq.py if needed
	else
		predictor_gekko  > "ftio_${NODES}.out" 2> "ftio_${NODES}.err"
		# 2>&1 | tee  ./ftio_${NODES}.txt
	fi 
}

# Function to handle SIGINT (Ctrl+C)
function handle_sigint {
	echo "Keyboard interrupt detected. Exiting script."
	exit 0
}

function check_finish() {
    # Set trap to handle SIGINT
    trap 'handle_sigint' SIGINT
	
	while :
	do
    if [ "$FINISH" = true ]; then
        echo "FINISH flag is true. Exiting script in 10 sec."
		sleep 10
        exit 0
    fi
	done 
}


function error_usage(){
	echo -e "Usage: $0 -a X.X.X.X -p X -n X \n 
	-a: X.X.X.X (ip address <string>: ${BLUE}${ADDRESS}${BLACK}) 
	-p: XXXX (port <int>: ${BLUE}${PORT}${BLACK})
	-n: X (Processes <int>: ${BLUE}${NODES}${BLACK})

	-i install everyting
\n---- exit ----
	"
}

function install_all(){
	
	# Clone GKFS
	echo -e "${GREEN}>>> Installing GEKKO${BLACK}"
	cd ${install_location}
	git clone --recurse-submodules https://storage.bsc.es/gitlab/hpc/gekkofs.git
	cd gekkofs
	git checkout fmt10
	git pull --recurse-submodules 
	cd ..

	# Build GKFS
	gekkofs/scripts/gkfs_dep.sh iodeps/git iodeps
	cd gekkofs && mkdir build && cd build
	cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=${install_location}/iodeps -DGKFS_BUILD_TESTS=OFF  -DCMAKE_INSTALL_PREFIX=${install_location}/iodeps -DGKFS_ENABLE_CLIENT_METRICS=ON ..
	make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
	echo -e "${GREEN}>>> GEKKO installed${BLACK}"

	#Cardo DEPS: CEREAL
	echo -e "${GREEN}>>> Installing Cargo${BLACK}"
	cd ${install_location}
	git clone https://github.com/USCiLab/cereal
	cd cereal && mkdir build && cd build
	cmake -DCMAKE_PREFIX_PATH=${install_location}/iodeps \
	-DCMAKE_INSTALL_PREFIX=${install_location}/iodeps ..
	make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
	
	#Cargo DEPS: THALLIUM
	cd ${install_location}
	git clone https://github.com/mochi-hpc/mochi-thallium
	cd mochi-thallium && mkdir build && cd build
	cmake -DCMAKE_PREFIX_PATH=${install_location}/iodeps \
	-DCMAKE_INSTALL_PREFIX=${install_location}/iodeps ..
	make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"

	# clone cargo:
	cd ${install_location}
	git clone https://storage.bsc.es/gitlab/hpc/cargo.git
	cd cargo
	git checkout rnou/40-interface-with-ftio
	cd ..

	# build cargo 
	cd cargo && mkdir build && cd build
	cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=${install_location}/iodeps 	-DCMAKE_INSTALL_PREFIX=${install_location}/iodeps ..
	make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
	# GekkoFS should be found in the cargo CMAKE configuration.
	echo -e "${GREEN}>>> Cargon installed${BLACK}"

	# build FTIO:
	echo -e "${GREEN}>>> Installing FTIO${BLACK}"
	cd ${install_location}
	git clone https://github.com/tuda-parallel/FTIO.git
	ml lang/Python/3.10.8-GCCcore-12.2.0 || echo "skipping module load";
	cd FTIO
	# Install FTIO
	make install  || echo -e "${RED}>>> Error encountered${BLACK}"
	echo -e "${GREEN}>>> FTIO installed${BLACK}"


	echo -e "call these two lines: \n 
	export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${install_location}/iodeps/lib:${install_location}/iodeps/lib64
	source ${install_location}/FTIO/.venv/activate

	read to go
	"
}

function parse_options(){
	# Parse command-line arguments using getopts
	while getopts ":a:p:n:i:h" opt; do
		case $opt in
		a) ADDRESS="$OPTARG" ;;
		p) PORT="$OPTARG" ;;
		n) NODES="$OPTARG" ;;
		i) 
			install_location="$OPTARG" 
			install_all 
			;;
		h) 
			echo -e "${YELLOW}Help launch:  ${BLACK}" >&2
			error_usage $OPTARG
			exit 1
			;;
		\?)
			echo -e "${RED}Invalid option: -$1 ${BLACK}" >&2
			error_usage $OPTARG
			exit 1
			;;
		esac
	done

	# Shift positional arguments to remove processed flags and options
	shift $((OPTIND - 1))
}

