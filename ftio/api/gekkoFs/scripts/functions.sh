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
		salloc -N $NODES -t ${MAX_TIME} --overcommit --oversubscribe --partition parallel -A nhr-admire --job-name JIT
		JIT_ID=$(squeue | grep "JIT" |awk '{print $(1) }')
		ALL_NODES=$(squeue --me -l |  head -n 3| tail -1 |awk '{print $NF}')
		# create array with start and end nodes
		NODES_ARR=($(echo $ALL_NODES | grep -Po '[\d]*'))
		# assign FTIO to the last node
		FTIO_NODE="cpu${NODES_ARR[-1]}"

		echo "${#start[@]}"
		if [ "${#ALL_NODES[@]}" -gt "1" ]; then
			EXCLUDE="--exclude=cpu${FTIO_NODE}"
		fi

		echo -e "
			${CYAN}JIT Job Id: ${JIT_ID} ${BLACK}\n
			${CYAN}Allocated Nodes: ${ALL_NODES} ${BLACK}\n
			${CYAN}FTIO Node: ${FTIO_NODE} ${BLACK}\n
			${CYAN}Exclude command: ${EXCLUDE} ${BLACK}\n\n
			"
	fi
}


# Start FTIO
function start_ftio() {
	echo -e "${GREEN}####### Starting FTIO ${BLACK}\n"
	# set -x
	if [ "$CLUSTER" = true ]; then
		source ${FTIO_ACTIVATE}
		# One node is only for FTIO
		echo -e "${GREEN}FTIO started on node, remainng nodes for the application:${NODES} ${BLACK}\n"
		NODES=$((${NODES} - 1))
		srun --jobid=${JIT_ID} --nodelist=${FTIO_NODE} --disable-status -N 1 --ntasks=1 --cpus-per-task=${PROCS} \
		--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
		predictor_gekko  --zmq_address ${ADDRESS} --zmq_port ${PORT}
		# Change CARGO path in predictor_gekko_zmq.py if needed
	else
		predictor_gekko  > "ftio_${NODES}.out" 2> "ftio_${NODES}.err"
		# 2>&1 | tee  ./ftio_${NODES}.txt
	fi 
	# set -o xtrace
}

# Start the Server
function start_geko() {
	echo -e "${GREEN}####### GKFS DEOMON started ${BLACK}"
	# set -x
	if [ "$CLUSTER" = true ]; then
		srun --jobid=${JIT_ID} ${EXCLUDE} --disable-status -N ${NODES} --ntasks=${NODES} --cpus-per-task=${PROCS} \
		--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
		${GKFS_DEMON}  \
		-r /dev/shm/tarraf_gkfs_rootdir \
		-m /dev/shm/tarraf_gkfs_mountdir \
		-H ${GKFS_HOSTFILE}  -c -l ib0
	else
		# Geko Demon call
			GKFS_DAEMON_LOG_LEVEL=info \
			${GKFS_DEMON} \
			-r /tmp/gkfs_rootdir \
			-m /tmp/gkfs_mountdir \
			-c --auto-sm \
			-H ${GKFS_HOSTFILE} 
	fi
	# set -o xtrace
}

# Application call
function start_application() {
	echo -e "${CYAN}Executing Application ${BLACK}"
	# set -x
	# application with Geko LD_PRELOAD
	# Same a comment as start_gekko like the dmon
	if [ "$CLUSTER" = true ]; then
		LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} \
			LIBGKFS_LOG=none \
			LIBGKFS_ENABLE_METRICS=on \
			LIBGKFS_METRICS_IP_PORT=${ADDRESS}:${PORT} \
			LD_PRELOAD=${GKFS_INERCEPT} \
			srun --jobid=${JIT_ID} ${EXCLUDE} --disable-status -N ${NODES} --ntasks=${NODES} --cpus-per-task=${PROCS} \
			--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
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
	# set -o xtrace
	FINISH=true
}

function start_cargo() {
	echo -e "${GREEN}####### Starting Cargo ${BLACK}"
	# set -x
	if [ "$CLUSTER" = true ]; then
		# One instance per node
		LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} \
			srun --jobid=${JIT_ID} ${EXCLUDE} --disable-status -N ${NODES} --ntasks=${NODES} --cpus-per-task=${PROCS} \
			--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
			--hostfile /lustre/project/nhr-admire/tarraf/hostfile \
			${CARGO} --listen \
			ofi+sockets://127.0.0.1:62000 \
	else
		mpiexec -np 2 --oversubscribe \
			--map-by node \
			-x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} \
			--hostfile /lustre/project/nhr-admire/tarraf/hostfile \
			${CARGO} --listen \
			ofi+sockets://127.0.0.1:62000 \
			>> ./cargo_${NODES}.txt
	fi
	# set -o xtrace
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
	make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
	echo -e "${GREEN}>>> GEKKO installed${BLACK}"

	#Cardo DEPS: CEREAL
	echo -e "${GREEN}>>> Installing Cargo${BLACK}"
	cd ${install_location}
	git clone https://github.com/USCiLab/cereal
	cd cereal && mkdir build && cd build
	-DCMAKE_INSTALL_PREFIX=${install_location}/iodeps ..
	make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
	
	#Cargo DEPS: THALLIUM
	cd ${install_location}
	git clone https://github.com/mochi-hpc/mochi-thallium
	cd mochi-thallium && mkdir build && cd build
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
	source ${install_location}/FTIO/.venv/activate

	read to go
	"
}

function parse_options(){
	# Parse command-line arguments using getopts
	while getopts ":a:p:n:t:i:h" opt; do
		case $opt in
		a) ADDRESS="$OPTARG" ;;
		p) PORT="$OPTARG" ;;
		n) NODES="$OPTARG" ;;
		t) MAX_TIME="$OPTARG" ;;
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

function find_time(){

	n=$1
	tm=0
    if [ $n -lt 101 ]; then
        tm=05
    elif [ $n -lt 1001 ]; then
        tm=30
    elif [ $n -lt 5001 ]; then
        tm=10   
    elif [ $n -lt 10001 ]; then
        tm=30   
    else
        #tm=$(($n / 100))
        tm=60
    fi

	return $tm
}

function shut_down(){
	local name=$1
	local PID=$2
	echo "Shutting down ${name} with PID ${PID}"
	if [[ -n ${PID}]]; then
		# kill -s SIGINT ${PID} &
		kill ${PID} 
		wait ${PID}
	fi
}


function get_id(){
	trueIdid=$(squeue | grep "APPXGEKKO" |awk '{print $(1) }')
	return $trueIdid
}

function info(){
	trueID=$(get_id)
	echo -e "${BLUE}\nWorking directory is -> $PWD ${BLACK}"
	echo -e "${BLUE}Target nodes ---------> $NODES ${BLACK}"
	echo -e "${BLUE}Max time -------------> $MAX_TIME ${BLACK}"
	echo -e "${BLUE}Job id ---------------> ${RED}$trueId \n ${BLACK}"
}


wait_for_gkfs_daemons() {
	sleep 2
    local server_wait_cnt=0
    local nodes=${NODES}
    until [ $(($(wc -l "${GKFS_HOSTFILE}"  2> /dev/null | awk '{print $1}') + 0)) -eq "${nodes}" ]
    do
        sleep 2
        server_wait_cnt=$((server_wait_cnt+1))
        if [ ${server_wait_cnt} -gt 600 ]; then
            echo "Server failed to start. Exiting ..."
            exit 1
        fi
    done
}

function progress(){
	Animationflag=0
	trueID=$(get_id)
	status=$(squeue| grep $trueId | awk '{print $5 }' | tail -1 )
	job_nodes=$(squeue  | grep $trueId | awk '{print $(9) }' | tail -1 )
	time_limit=$(squeue | grep $trueId | awk '{print $(7) }' | tail -1 )
	while [[ $status != "C" ]] &&  [[ $status != "F" ]] &&  [[ $status != "S" ]] && [[ ! -z $status ]]; do
        if [[ $status == *R* ]]; then
            if [[ flag -eq 0 ]]; then
		start_time="$(date -u +%s)"
		flag=1
                echo -e "\n${BLUE}  RUNNING on $job_nodes nodes${BLACK}"
            fi
            end_time="$(date -u +%s)"
            echo -en "\r${CYAN}  Running --> elapsed time:[ $(($end_time - $start_time)) / $(($((10#$tm)) * 60 + $((10#$th)) * 3600)) ] seconds ${BLACK}"
        
        elif [[ $status == *PD* ]]; then
            if [[ $Animationflag -eq 0 ]]; then
                echo -en "\r  PENDING  \  "
                Animationflag=1
            elif [[ $Animationflag -eq 1 ]]; then
                echo -en "\r  PENDING  |  "
                Animationflag=2
            elif [[ $Animationflag -eq 2 ]]; then
                echo -en "\r  PENDING  /  "
                Animationflag=3
            else
                echo -en "\r  PENDING  -  "
                Animationflag=0
            fi
        
        elif [[ $status == *C* ]]; then
            echo -e "\n  CONFIGURING  "
        
        elif [[ $status == *F* ]]; then
            echo "  --FAILED--"
            #break
            exit [0]
        
        else
            echo "  $status"
        fi

        # Sleep for few seconds
        #if [[ $((tm / 5)) -eq 0 ]]; then
        if [[ $MAX_TIME -lt 60 ]]; then
			sleep 1
        else
            sleep $(  echo "($MAX_TIME)/20" | bc -l )
	fi

	status=$(squeue| grep $trueId | awk '{print $5 }' | tail -1 )
    done

    echo -e "${GREEN}\n  ---- Simulation complete ----${BLACK}"
    
    time=$(squeue | grep $trueId | awk '{print $(6) }' |  tail -1 )
    if [[ -z "$time" ]]; then
		time=$(squeue | awk '{print $(6) }' |  tail -1 )
    fi
	echo -e "${BLUE}  Finished run with $job_nodes nodes in $time / $time_limit${BLACK}"
}