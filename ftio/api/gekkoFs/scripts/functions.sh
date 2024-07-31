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
        echo -e "${RED}Error: Port $PORT is already in use on ${ADDRESS_FTIO}. Terminating existing process...${BLACK}"
        
        # Use ss command for potentially more reliable process identification (uncomment)
        # process_id=$(ss -tlpn | grep :"$PORT " | awk '{print $NF}')
        
        # Use netstat if ss is unavailable (uncomment)
        # process_id=$(netstat -tlpn | grep :"$PORT " | awk '{print $7}' | cut -d'/' -f1)
		process_id=$(netstat -nlp | grep :"$PORT " | awk '{print $7}' | cut -d'/' -f1)
        
        if [[ ! -z "$process_id" ]]; then
            echo -e "${YELLOW}Terminating process with PID: $process_id${BLACK}"
            kill ${process_id} && echo -e "${GREEN}Using $PORT on ${ADDRESS_FTIO}.${BLACK}"
            return 0
        else
            echo -e "${RED}Failed to identify process ID for PORT $PORT.${BLACK}"
        fi
        exit 1
    else
        echo -e "${GREEN}Using $PORT on ${ADDRESS_FTIO}.${BLACK}"
    fi
}


function allocate(){
	APP_NODES=1

    if [ "$CLUSTER" == true ]; then
		echo -e "\n${JIT} ${BLUE}####### Allocating resources${BLACK}"

		call="salloc -N ${NODES} -t ${MAX_TIME} ${ALLOC_CALL_FLAGS}"

		echo -e "${JIT}${CYAN} >> Executing: ${call} ${BLACK}"
        # salloc -N ${NODES} -t ${MAX_TIME} --overcommit --oversubscribe --partition parallel -A nhr-admire --job-name JIT --no-shell
		eval " ${call}"
		
		# Format to output job information, including the job ID, partition, job name, user, state, time used, nodes, and reason. Afterwards, 
		# sorts the filtered lines by job ID in reverse numerical order, ensuring that the latest job (with the highest job ID) comes first. 
		# Head takes the first line from the sorted output, which corresponds to the most recent job with the name "JIT".
		JIT_ID=$(squeue -o "%.18i %.9P %.8j %.8u %.2t %.10M %.6D %R" | grep ' JIT ' | sort -k1,1rn | head -n 1 | awk '{print $1}')
		
		# JIT_ID=$(squeue | grep "JIT" |awk '{print $(1)}' | tail -1)
		# #old
        # ALL_NODES=$(squeue --me -l |  head -n 3| tail -1 |awk '{print $NF}')
        # # create array with start and end nodes
		# only works for continous 
        # NODES_ARR=($(echo $ALL_NODES | grep -Po '[\d]*'))
		# better solution
		NODES_ARR=($(scontrol show hostname $(squeue -j ${JIT_ID} -o "%N" | tail -n +2)))
		
		# MPI needs to know the nodes to run on --> create hostfile
		scontrol show hostname $(squeue -j ${JIT_ID} -o "%N" | tail -n +2) > ~/hostfile_mpi
		# scontrol show hostname $(squeue -j $SLURM_JOB_ID -o "%N" | tail -n +2) > ~/hostfile_mpi
        
		# Get FTIO node
		FTIO_NODE="${NODES_ARR[-1]}"
		SINGLE_NODE="${NODES_ARR[0]}"	

        if [ "${#NODES_ARR[@]}" -gt "1" ]; then
            
			# # Exclude 
			# APP_NODES_COMMAND="--exclude=${FTIO_NODE}"
			# FTIO_NODE_COMMAND="--exclude=$(echo ${NODES_ARR[@]/${FTIO_NODE}} | tr ' ' ',' )"
			# or include 
			
			FTIO_NODE_COMMAND="--nodelist=${FTIO_NODE}"
			APP_NODES_COMMAND="--nodelist=$(echo ${NODES_ARR[@]/${FTIO_NODE}} | tr ' ' ',' )"
			SINGLE_NODE_COMMAND="--nodelist=${SINGLE_NODE}"
			
			APP_NODES=$((${NODES} - 1))
			sed  -i "/${FTIO_NODE}/d" ~/hostfile_mpi
        fi
        
        echo -e "${JIT}${GREEN} >> JIT Job Id: ${JIT_ID} ${BLACK}"
		echo -e "${JIT}${GREEN} >> Allocated Nodes: "${#NODES_ARR[@]}" ${BLACK}"
		echo -e "${JIT}${GREEN} >> FTIO Node: ${FTIO_NODE} ${BLACK}"
		echo -e "${JIT}${GREEN} >> APP  Node command: ${APP_NODES_COMMAND} ${BLACK}"
		echo -e "${JIT}${GREEN} >> FTIO Node command: ${FTIO_NODE_COMMAND} ${BLACK}"
		echo -e "${JIT}${GREEN} >> cat ~/hostfile_mpi: \n$(cat ~/hostfile_mpi) ${BLACK}\n"	
	fi
}


# Start FTIO
function start_ftio() {
	if [ "$EXCLUDE_FTIO" == true ] || [ "${EXCLUDE_ALL}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping FTIO ${BLACK}"
	 
	 	if [ "${EXCLUDE_ALL}" == false ]; then
			echo -e "\n${JIT}${YELLOW}WARNING: Executing the calls bellow though it might be probability not needed${BLACK}"
			call_0="${PRECALL} srun --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${CARGO_CLI}/cargo_ftio --server ${CARGO_SERVER} --run"
			call_1="${PRECALL} srun --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${CARGO_CLI}/ccp --server ${CARGO_SERVER} --input / --output ${STAGE_OUT_PATH} --if gekkofs --of parallel"
			execute "${call_0}"
			execute "${call_1}"
		fi
	else		
		echo -e "\n${JIT}${BLUE} ####### Starting FTIO ${BLACK}"
		# set -x
		if [ "$CLUSTER" == true ]; then
			source ${FTIO_ACTIVATE}
			
			# One node is only for FTIO
			echo -e "${JIT}${CYAN} >> FTIO started on node ${FTIO_NODE}, remainng nodes for the application: ${APP_NODES} each with ${PROCS} processes ${BLACK}"
			echo -e "${JIT}${CYAN} >> FTIO is listening node is ${ADDRESS_FTIO}:${PORT} ${BLACK}"

			# call
			call="srun --jobid=${JIT_ID} ${FTIO_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 predictor_jit  --zmq_address ${ADDRESS_FTIO} --zmq_port ${PORT} --cargo_cli ${CARGO_CLI} --cargo_server ${CARGO_SERVER} --cargo_out ${STAGE_OUT_PATH} "
		else
			#clean port 
			check_port			
			call="predictor_jit  --zmq_address ${ADDRESS_FTIO} --zmq_port ${PORT}"
			# 2>&1 | tee  ./ftio_${NODES}.txt
		fi
		# set -o xtrace
		echo -e "${JIT}${CYAN} >> Executing: ${call} ${BLACK}"
		eval " ${call}"
		echo -e "\n\n"
	fi 
}

# Start the Server
function start_geko_demon() {
	if [ "${EXCLUDE_ALL}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping GKFS DEMON ${BLACK}"
	else
		echo -e "\n${JIT}${BLUE} ####### Starting GKFS DEOMON ${BLACK}"
		# set -x
		if [ "$CLUSTER" == true ]; then
			# Display Demon
			call_0="srun --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} -N 1 --ntasks=1 mkdir -p ${GKFS_MNTDIR}"
			
			# Demon call
			call="srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${GKFS_DEMON}  -r ${GKFS_ROOTDIR} -m ${GKFS_MNTDIR} -H ${GKFS_HOSTFILE}  -c -l ib0 -P ofi+sockets -p ofi+verbs -L ib0"
			# #
			# # old
			# srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS} \
			# --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
			# ${GKFS_DEMON}  \
			# -r ${GKFS_ROOTDIR} \
			# -m ${GKFS_MNTDIR} \
			# -H ${GKFS_HOSTFILE}  -c -l ib0 \
			# -P ofi+sockets -p ofi+verbs -L ib0
		else
			call_0="mkdir -p ${GKFS_MNTDIR}"

			# Geko Demon call
			# call="GKFS_DAEMON_LOG_LEVEL=info ${GKFS_DEMON} -r ${GKFS_ROOTDIR} -m ${GKFS_MNTDIR} -H ${GKFS_HOSTFILE} -p ofi+tcp" 
			call="GKFS_DAEMON_LOG_LEVEL=info ${GKFS_DEMON} -r ${GKFS_ROOTDIR} -m ${GKFS_MNTDIR} -H ${GKFS_HOSTFILE} -l lo -c -P ofi+tcp --proxy-listen lo --proxy-protocol ofi+tcp"
			#-c --auto-sm
		fi
		execute "${call_0}" "Creating directory"
		execute "${call}"
		echo -e "\n\n"
	fi 
}


function start_geko_proxy() {
	
	if [ "${EXCLUDE_ALL}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping GKFS PROXY ${BLACK}"
	else
		echo -e "\n${JIT}${BLUE} ####### Starting GKFS PROXY ${BLACK}"
		if [ "$CLUSTER" == true ]; then
			# Proxy call
			call="srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${GKFS_PROXY}  -H ${GKFS_HOSTFILE} -p ofi+verbs -P ${GKFS_PROXYFILE}"
			#
			# old
			# srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS} \
			# --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
			# ${GKFS_PROXY}  \
			# -H ${GKFS_HOSTFILE} -p ofi+verbs -P ${GKFS_PROXYFILE}
		else
			
			call="${GKFS_PROXY} -H ${GKFS_HOSTFILE} -p ofi+tcp -P ${GKFS_PROXYFILE}" 
		fi
		echo -e "${JIT}${CYAN} >> Executing: ${call} ${BLACK}"
		eval " ${call}"
		echo -e "\n\n"
	fi
}



function start_cargo() {
    if [ "${EXCLUDE_ALL}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping Cargo ${BLACK}"
	else
		echo -e "\n${JIT}${BLUE} ####### Starting Cargo ${BLACK}"
		# set -x
		if [ "$CLUSTER" == true ]; then
			
			# One instance per node
			call="srun --export=LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LD_LIBRARY_PATH=${LD_LIBRARY_PATH} --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0  ${CARGO} --listen ofi+sockets://ib0:62000 -b 65536"
			# --mem=0  ${CARGO} --listen ofi+sockets://127.0.0.1:62000 -b 65536"
			
			# -b specifies block size to move 64MiB 
			
			#
			# old
			# srun --export=LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LD_LIBRARY_PATH=${LD_LIBRARY_PATH} \
			# --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} \
			# --ntasks=${APP_NODES} --cpus-per-task=${PROCS} \
			# --ntasks-per-node=1 --overcommit --overlap --oversubscribe \
			# --mem=0  ${CARGO} --listen ofi+sockets://127.0.0.1:62000 
		else
			call="mpiexec -np 1 --oversubscribe -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} ${CARGO} --listen ofi+sockets://127.0.0.1:62000 -b 65536"
		fi
		# set -o xtrace
		echo -e "${JIT}${CYAN} >> Executing: ${call} ${BLACK}"
		eval " ${call}"
		echo -e "\n\n"
	fi
}



# Application call
function start_application() {
    echo -e "\n${JIT}${BLUE} ####### Executing Application ${BLACK}"
    # set -x
    if [ "$CLUSTER" == true ]; then
		# display hostfile
		if [ "${EXCLUDE_ALL}" == false ]; then
			echo -e "${JIT}${BLUE} >> MPI hostfile: \n$(cat ~/hostfile_mpi) ${BLACK}\n"
			echo -e "${JIT}${BLUE} >> Gekko hostfile:\n$(cat ${GKFS_HOSTFILE}) ${BLACK}\n"
			local files=$(LD_PRELOAD=${GKFS_INTERCEPT}  LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE}  ls ${GKFS_MNTDIR})
			echo -e "${JIT}${BLUE} Files in ${GKFS_MNTDIR}: \n${files} ${BLACK}\n"
		fi
		
		sleep 5

		# without FTIO
		#? [--stag in--]               [--stag out--]
		#?              [---nek5000---]
		# with FTIO
		#? [--stag in--]   [so]  [so] ... [so]
		#?              [---nek5000---]
		
		# with srun
        # call="srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS}  --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 --export=ALL,LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LD_LIBRARY_PATH=${LD_LIBRARY_PATH},LD_PRELOAD=${GKFS_INTERCEPT},LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE},LIBGKFS_ENABLE_METRICS=on,LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT} ${APP_CALL}"
		
		#original:
		# call="srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS}  --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 --export=ALL,LD_PRELOAD=${GKFS_INTERCEPT},LIBGKFS_LOG=errors,LIBGKFS_LOG_OUTPUT=~/tarraf_gkfs_client.log,LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE},LIBGKFS_ENABLE_METRICS=on,LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT},LD_LIBRARY_PATH=${LD_LIBRARY_PATH}  ${APP_CALL}"

		# call="LIBGKFS_LOG=errors,warnings LIBGKFS_LOG_OUTPUT=~/tarraf_gkfs_client.log LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE} LIBGKFS_ENABLE_METRICS=on LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT} LD_PRELOAD=${GKFS_INTERCEPT}  srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS}  --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 --export=LD_LIBRARY_PATH=${LD_LIBRARY_PATH} ${APP_CALL}"

		# app call
		if [ "${EXCLUDE_ALL}" == true ]; then
			# run without jit tools
			call="cd /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs; ${PRECALL} mpiexec -np ${PROCS} --oversubscribe --hostfile ~/hostfile_mpi --map-by node ${APP_CALL}"
		else
			# run with jit tools
			call="cd /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs; ${PRECALL} mpiexec -np ${PROCS} --oversubscribe --hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=errors,warnings -x LIBGKFS_ENABLE_METRICS=on -x LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT} -x LD_PRELOAD=${GKFS_INTERCEPT} -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE} ${APP_CALL}"
		fi
		# old
		# ${PRECALL} mpiexec -np ${PROCS} --oversubscribe \
		# --hostfile ~/hostfile_mpi \
		# --map-by node -x LIBGKFS_LOG=errors,warnings \
		# -x LIBGKFS_ENABLE_METRICS=on \
		# -x LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT}\
		# -x LD_PRELOAD=${GKFS_INTERCEPT}\
		# -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE}\
		# -x LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE}\
		# ${APP_CALL}
		
		# measure stage-out

    else
        # app call
		if [ "${EXCLUDE_ALL}" == true ]; then
			call="mpiexec -np ${APP_NODES} --oversubscribe ${APP_CALL}"
		else
			call="mpiexec -np ${APP_NODES} --oversubscribe -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LIBGKFS_LOG=none -x LIBGKFS_ENABLE_METRICS=on -x LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT} -x LD_PRELOAD=${GKFS_INTERCEPT} ${APP_CALL}"
		fi
    fi

	echo -e "${JIT}${CYAN} >> Executing: ${call} ${BLACK}"
	start=$(date +%s.%N | { read -r secs_nanos; secs=${secs_nanos%.*}; nanos=${secs_nanos#*.}; printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null; })
	eval " ${call}"
	end=$(date +%s.%N | { read -r secs_nanos; secs=${secs_nanos%.*}; nanos=${secs_nanos#*.}; printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null; })
    FINISH=true
	
	elapsed_time "Application finished" ${start} ${end}
}


function stage_out() {
	
	if [ "${EXCLUDE_ALL}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping Stage out ${BLACK}"
	else
		echo -e "\n${JIT}${YELLOW} ####### Stagin out ${BLACK}"
		
		# stage out call on any compute node
		if [ "$CLUSTER" == true ]; then
			call="${PRECALL} srun --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${CARGO_CLI}/cargo_ftio --server ${CARGO_SERVER} --run"
		else
			call="${PRECALL} mpiexec -np 1 --oversubscribe ${CARGO_CLI}/cargo_ftio --server ${CARGO_SERVER} --run"
		fi
		
		echo -e "${JIT}${CYAN} > Satgging out: ${call} ${BLACK}"
		start=$(date +%s.%N | { read -r secs_nanos; secs=${secs_nanos%.*}; nanos=${secs_nanos#*.}; printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null; })
		eval " ${call}"
		end=$(date +%s.%N | { read -r secs_nanos; secs=${secs_nanos%.*}; nanos=${secs_nanos#*.}; printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null; })
		elapsed_time "Stage out" ${start} ${end}
	fi 
}

function stage_in() {
	if [ "${EXCLUDE_ALL}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping Stage in ${BLACK}"
	else
		echo -e "\n${JIT}${YELLOW} ####### Stagin in ${BLACK}"
		
		# stage in call on any compute node
		if [ "$CLUSTER" == true ]; then

			call="${PRECALL} srun --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${CARGO_CLI}/ccp --server ${CARGO_SERVER} --output / --input ${STAGE_IN_PATH} --of gekkofs --if parallel"
			# call="LD_PRELOAD=${GKFS_INTERCEPT}  LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE}  cp -r ${STAGE_IN_PATH}/* ${GKFS_MNTDIR}"
			# call="srun --export=LD_LIBRARY_PATH=${LD_LIBRARY_PATH},LD_PRELOAD=${GKFS_INTERCEPT},LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 /usr/bin/cp -r ${STAGE_IN_PATH}/* ${GKFS_MNTDIR}"
		else
			call="${PRECALL} mpiexec -np 1 --oversubscribe ${CARGO_CLI}/ccp --server ${CARGO_SERVER} --output / --input ${STAGE_IN_PATH}  --of gekkofs --if parallel"
		fi
		
		echo -e "${JIT}${CYAN} > Satgging in: ${call} ${BLACK}"
		start=$(date +%s.%N | { read -r secs_nanos; secs=${secs_nanos%.*}; nanos=${secs_nanos#*.}; printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null; })
		eval " ${call}"
		end=$(date +%s.%N | { read -r secs_nanos; secs=${secs_nanos%.*}; nanos=${secs_nanos#*.}; printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null; })
		elapsed_time "Stage in" ${start} ${end}
		
		local files=$(LD_PRELOAD=${GKFS_INTERCEPT}  LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE}  ls ${GKFS_MNTDIR})
		echo -e "${JIT}${BLUE} Files in ${GKFS_MNTDIR}: \n${files} ${BLACK}\n"
	fi
}


#precall
function pre_call() {
	if [ -n "${PRE_APP_CALL}" ]; then
		echo -e "\n${JIT}${YELLOW} ####### Pre-application Call ${BLACK}"
		execute "${PRE_APP_CALL}"
	fi 
}

# post call
function post_call() {
	if [ -n "${POST_APP_CALL}" ]; then
		echo -e "\n${JIT}${YELLOW} ####### Post-application Call ${BLACK}"
		execute " ${POST_APP_CALL}"
	fi
}


function soft_kill() {
	echo -e "\n${JIT}${BLUE} ####### Soft kill ${BLACK}"
	shut_down "FTIO" ${FTIO_PID} &
	shut_down "GEKKO" ${GEKKO_DEMON_PID} &
	shut_down "GEKKO" ${GEKKO_PROXY_PID} &
	shut_down "CARGO" ${CARGO_PID} &
}

function hard_kill() {
	if [ "$CLUSTER" == true ]; then
		echo -e "\n${JIT}${BLUE} ####### Hard kill ${BLACK}"
		scancel ${JIT_ID} || true 
	else 
		echo -e "\n${JIT}${BLUE} ####### Hard kill ${BLACK}"
		kill $(ps -aux | grep ${GKFS_DEMON}| grep -v grep | awk '{print $2}') || true
		kill $(ps -aux | grep ${GKFS_PROXY}| grep -v grep | awk '{print $2}') || true
		kill $(ps -aux | grep ${CARGO}| grep -v grep | awk '{print $2}') || true
		kill $(ps -aux | grep "$(dirname "$FTIO_ACTIVATE")/predictor_jit"| grep -v grep | awk '{print $2}') || true
	fi
}
# Function to handle SIGINT (Ctrl+C)
function handle_sigint {
    echo "${JIT} > Keyboard interrupt detected. Exiting script."
	scancle ${JIT_ID}
    exit 0
}

function check_finish() {
    # Set trap to handle SIGINT
    trap 'handle_sigint' SIGINT
    
    while :
    do
        if [ "$FINISH" == true ]; then
            echo "${JIT} > FINISH flag is true. Exiting script in 10 sec."
            sleep 10
            exit 0
        fi
    done
}


function error_usage(){
    echo -e "Usage: $0 -a X.X.X.X -p X -n X \n
	-a | --address: X.X.X.X <string>
		Address where FTIO is executed 
		default: ${BLUE}${ADDRESS_FTIO}${BLACK}
		on a cluster, this is found automatically by determining
		the adrees of node where FTIO runs 

	-p | --port: XXXX <int>
		port for ftio and gekko 
		default: ${BLUE}${PORT}${BLACK}

	-n | --nodes: X <int>
		default: ${BLUE}${NODES}${BLACK}
		number of nodes to run the setup. in cluster mode, FTIO is 
		executed on a single node, while the rest (including the
		application) get X-1 nodes

	-t | --max-time: X <int>
		default: ${BLUE}${MAX_TIME}${BLACK}
		max time for the execution of the setup in minutes
	
	-l |--log-name: <str>
		default: autoset to number of nodes and job id
		if provided, sets the name of the directory were the logs are

	-e | --execlude-ftio: <bool>
		deafult: ${EXCLUDE_FTIO}
		if this flag is provided, the setup is executed without FTIO

	-x | --exclude-all
		deafult: ${EXCLUDE_ALL}
		if this flag is provided, the setup is executed without FTIO, GekkoFs, and Cargo

	-i | l-location: full_path <str>
		deafult: ${BLUE}${INSTALL_LOCATION}${BLACK}
		installs everyting in the provided directory

\n---- exit ----
    "
}

abort()
{
    echo >&2 '
***************
*** ABORTED ***
***************
'
    echo "An error occurred. Exiting..." >&2
    exit 1
}

function install_all(){
    #create dir
	trap 'abort' 0
	set -e #exit on fail

	echo -e "${JIT}${GREEN} >> Installation stated${BLACK}"
	echo -e "${JIT}${GREEN} >>> Creating directory${BLACK}"
	mkdir -p ${INSTALL_LOCATION}

    # Clone GKFS
    echo -e "${JIT}${GREEN} >>> Installing GEKKO${BLACK}"
    cd ${INSTALL_LOCATION}
    git clone --recurse-submodules https://storage.bsc.es/gitlab/hpc/gekkofs.git
    cd gekkofs
    # git checkout main fmt10
    git pull --recurse-submodules
	cd ..
    

	# Workaround for lib fabric
	# echo -e "${RED}>>> Work around for libfabric${BLACK}"
	# sed  -i '/\[\"libfabric/d' ${INSTALL_LOCATION}/gekkofs/scripts/profiles/latest/default_zmq.specs
	# sed  -i 's/\"libfabric\"//g' ${INSTALL_LOCATION}/gekkofs/scripts/profiles/latest/default_zmq.specs
    
    # Build GKFS
    gekkofs/scripts/gkfs_dep.sh -p default_zmq ${INSTALL_LOCATION}/iodeps/git ${INSTALL_LOCATION}/iodeps
	cd gekkofs && mkdir build && cd build
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=${INSTALL_LOCATION}/iodeps -DGKFS_BUILD_TESTS=OFF -DCMAKE_INSTALL_PREFIX=${INSTALL_LOCATION}/iodeps -DGKFS_ENABLE_CLIENT_METRICS=ON ..
    make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"	
    echo -e "${JIT}${GREEN} >>> GEKKO installed${BLACK}"
    
    #Cardo DEPS: CEREAL
    echo -e "${JIT}${GREEN} >>> Installing Cargo${BLACK}"
    cd ${INSTALL_LOCATION}
    git clone https://github.com/USCiLab/cereal
    cd cereal && mkdir build && cd build
    cmake -DCMAKE_PREFIX_PATH=${INSTALL_LOCATION}/iodeps -DCMAKE_INSTALL_PREFIX=${INSTALL_LOCATION}/iodeps ..
    make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
    
    #Cargo DEPS: THALLIUM
    cd ${INSTALL_LOCATION}
    git clone https://github.com/mochi-hpc/mochi-thallium
    cd mochi-thallium && mkdir build && cd build
	cmake -DCMAKE_PREFIX_PATH=${INSTALL_LOCATION}/iodeps -DCMAKE_INSTALL_PREFIX=${INSTALL_LOCATION}/iodeps ..    
    make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
    
    # clone cargo:
    cd ${INSTALL_LOCATION}
    git clone https://storage.bsc.es/gitlab/hpc/cargo.git
    cd cargo
    git checkout rnou/fmt10
	cd ..
    
    # build cargo
    cd cargo && mkdir build && cd build
	cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=${INSTALL_LOCATION}/iodeps -DCMAKE_INSTALL_PREFIX=${INSTALL_LOCATION}/iodeps ..
    make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
    # GekkoFS should be found in the cargo CMAKE configuration.
    echo -e "${JIT}${GREEN} >>> Cargon installed${BLACK}"
    
    ## build FTIO:
    # echo -e "${GREEN}>>> Installing FTIO${BLACK}"
    # cd ${INSTALL_LOCATION}
    # git clone https://github.com/tuda-parallel/FTIO.git
    # ml lang/Python/3.10.8-GCCcore-12.2.0 || echo "skipping module load";
    # cd FTIO
    # # Install FTIO
    # make install  || echo -e "${RED}>>> Error encountered${BLACK}"
    # echo -e "${GREEN}>>> FTIO installed${BLACK}"
    
    #build IOR
	cd ${INSTALL_LOCATION}
	git clone https://github.com/hpc/ior.git
	cd ior 
	./bootstrap
	./configure
	make -j 4 #&& make -j 4 install 

	echo -e "${JIT}${GREEN} >> Installation finished${BLACK}"
    echo -e "\n
	>> read to go <<
	call: ./jit.sh  -n NODES -t MAX_TIME 
    "
	trap : 0
}
function parse_options() {
    # Define the options
    OPTIONS=a:p:n:t:l:i:exh
    LONGOPTS=address:,port:,nodes:,max-time:,log-name:,install-location:,exclude-ftio,exclude-all,help

    # -temporarily store output to be able to check for errors
    # -activate advanced mode getopt quoting e.g. via “--options”
    # -pass arguments only via   -- "$@"
    PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
    if [[ $? -ne 0 ]]; then
        # getopt has complained about wrong arguments to stdout
        exit 2
    fi
    # read getopt’s output this way to handle the quoting right:
    eval set -- "$PARSED"

    # now enjoy the options in order and nicely split until we see --
    while true; do
        case "$1" in
            -a|--address)
                ADDRESS_FTIO="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -n|--nodes)
                NODES="$2"
                shift 2
                ;;
            -t|--max-time)
                MAX_TIME="$2"
                shift 2
                ;;
			-l|--log-name)
                LOG_DIR="$2"
                shift 2
                ;;
            -i|--install-location)
                INSTALL_LOCATION="$2"
                install_all
                shift 2
                ;;
			-e|--exclude-ftio)
                EXCLUDE_FTIO=true
                shift
                ;;
			-x|--exclude-all)
                EXCLUDE_ALL=true
                shift
                ;;
            -h|--help)
                echo -e "${YELLOW}Help launch:  ${BLACK}" >&2
                error_usage $OPTARG
                exit 1
                ;;
            --)
                shift
                break
                ;;
            *)
                echo -e "${RED}Invalid option: -$1 ${BLACK}" >&2
                error_usage $OPTARG
                exit 1
                ;;
        esac
    done
}

# function parse_options(){
#     # Parse command-line arguments using getopts
#     while getopts ":a:p:n:t:i:h" opt; do
#         case $opt in
#             a) ADDRESS_FTIO="$OPTARG" ;;
#             p) PORT="$OPTARG" ;;
#             n) NODES="$OPTARG" ;;
#             t) MAX_TIME="$OPTARG" ;;
#             i)
#                 INSTALL_LOCATION="$OPTARG"
#                 install_all
#             ;;
#             h)
#                 echo -e "${YELLOW}Help launch:  ${BLACK}" >&2
#                 error_usage $OPTARG
#                 exit 1
#             ;;
#             \?)
#                 echo -e "${RED}Invalid option: -$1 ${BLACK}" >&2
#                 error_usage $OPTARG
#                 exit 1
#             ;;
#         esac
#     done
    
#     # Shift positional arguments to remove processed flags and options
#     shift $((OPTIND - 1))
# }

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
    if [[ -n ${PID} ]]; then
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

function create_hostfile(){
	echo -e "${JIT}${CYAN} >> Cleaning Hostfile: ${GKFS_HOSTFILE} ${BLACK}"
	rm -f ${GKFS_HOSTFILE} || echo -e "${BLUE}>> No hostfile found ${BLACK}"
	
	# echo -e "${CYAN}>> Creating Hostfile: ${GKFS_HOSTFILE} ${BLACK}"
	# touch ${GKFS_HOSTFILE}
	# for i in "${NODES_ARR[@]::${#NODES_ARR[@]}-1}"; do #exclude last element as this is FTIO_NODE
   	# 	echo "cpu$i" >> ${GKFS_HOSTFILE}
	# done
}

function check_error_free(){
	if [ $? -eq 0 ] 
	then 
  		echo -e "${JIT}${GREEN} >> $1 successful ${BLACK}"
	else 
  		echo -e "${JIT}${RED} >> $1 failed! Exiting ${BLACK}<<<">&2 
  		exit 1 
	fi
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

function get_address_ftio(){
	# get Address and port
	echo -e "\n${BLUE}####### Getting FTIO ADDRESS ${BLACK}"
	if [ "$CLUSTER" == true ]; then
		# out = $(srun --jobid=${JIT_ID} ${EXCLUDE_FTIO} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ip addr | grep ib0 | awk '{print $2}'| cut -d'/' -f1 | tail -1)
		call="srun --jobid=${JIT_ID} ${FTIO_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ip addr | grep ib0 | awk '{print \$2}'| cut -d'/' -f1 | tail -1"
		echo -e "${JIT}${CYAN} >> Executing: ${call} ${BLACK}"
		# ADDRESS_FTIO=$(eval " ${call}" | awk '{print $NF}')
		ADDRESS_FTIO=$(eval " ${call}")
	else
		echo "using default address"
	fi 

	echo -e "${JIT} ${GREEN}>> ADDRESS_FTIO: ${ADDRESS_FTIO}${BLACK}"
}


function get_address_cargo(){
	echo -e "\n${BLUE}####### Getting Cargo ADDRESS ${BLACK}"
	if [ "$CLUSTER" == true ]; then
		call="srun --jobid=${JIT_ID}  ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ip addr | grep ib0 | awk '{print \$2}'| cut -d'/' -f1 | tail -1"
		echo -e "${JIT}${CYAN} >> Executing: ${call} ${BLACK}"
		ADDRESS_CARGO=$(eval " ${call}")
		CARGO_SERVER="ofi+sockets://${ADDRESS_CARGO}:62000"
	else
		echo "using default address"
	fi 

	echo -e "${JIT} ${GREEN}>> ADDRESS_CARGO: ${ADDRESS_CARGO}${BLACK}"
	echo -e "${JIT} ${GREEN}>> CARGO_SERVER:  ${CARGO_SERVER}${BLACK}"
}


function format_time() {
    local input_time="$1"
    local int_time="${input_time%.*}"
    local nanos="${input_time#*.}"
    
	local h=$(bc <<< "${int_time}/3600")
    local m=$(bc <<< "(${int_time}%3600)/60")
    local s=$(bc <<< "${int_time}%60")
    local out=$(printf "%02d:%02d:%02d.%s\n" $h $m $s $nanos)
    echo "${out}"
}

function print_settings(){

local ftio_status="${GREEN}ON${BLACK}"
local gkfs_status="${GREEN}ON${BLACK}"
local cargo_status="${GREEN}ON${BLACK}"

local ftio_text="
├─ FTIO_ACTIVATE  : ${BLUE}${FTIO_ACTIVATE}${BLACK}
├─ ADDRESS_FTIO   : ${BLUE}${ADDRESS_FTIO}${BLACK}
├─ PORT           : ${BLUE}${PORT}${BLACK}
├─ # NODES        : ${BLUE}1${BLACK}
└─ FTIO NODE      : ${BLUE}${FTIO_NODE_COMMAND##'--nodelist='}${BLACK}"

local gkfs_text="
├─ GKFS_DEMON     : ${BLUE}${GKFS_DEMON}${BLACK}
├─ GKFS_INTERCEPT : ${BLUE}${GKFS_INTERCEPT}${BLACK}
├─ GKFS_MNTDIR    : ${BLUE}${GKFS_MNTDIR}${BLACK}
├─ GKFS_ROOTDIR   : ${BLUE}${GKFS_ROOTDIR}${BLACK}
├─ GKFS_HOSTFILE  : ${BLUE}${GKFS_HOSTFILE}${BLACK}
├─ GKFS_PROXY     : ${BLUE}${GKFS_PROXY}${BLACK}
└─ GKFS_PROXYFILE : ${BLUE}${GKFS_PROXYFILE}${BLACK}"

local cargo_text="
├─ CARGO location : ${BLUE}${CARGO}${BLACK}${BLACK}
├─ CARGO_CLI      : ${BLUE}${CARGO_CLI}${BLACK}
├─ STAGE_IN_PATH  : ${BLUE}${STAGE_IN_PATH}${BLACK}
└─ ADDRESS_CARGO  : ${BLUE}${ADDRESS_CARGO}${BLACK}"

if [ "$EXCLUDE_FTIO" == true ] || [ "${EXCLUDE_ALL}" == true ] ; then
	ftio_text="
├─ FTIO_ACTIVATE  : ${YELLOW}none${BLACK}
├─ ADDRESS_FTIO   : ${YELLOW}none${BLACK}
├─ PORT           : ${YELLOW}none${BLACK}
├─ # NODES        : ${YELLOW}none${BLACK}
└─ FTIO NODE      : ${YELLOW}none${BLACK}"

ftio_status="${YELLOW}OFF${BLACK}"
fi


if [ "${EXCLUDE_ALL}" == true ] ; then
	gkfs_text="
├─ GKFS_DEMON     : ${YELLOW}none${BLACK}
├─ GKFS_INTERCEPT : ${YELLOW}none${BLACK}
├─ GKFS_MNTDIR    : ${YELLOW}none${BLACK}
├─ GKFS_ROOTDIR   : ${YELLOW}none${BLACK}
├─ GKFS_HOSTFILE  : ${YELLOW}none${BLACK}
├─ GKFS_PROXY     : ${YELLOW}none${BLACK}
└─ GKFS_PROXYFILE : ${YELLOW}none${BLACK}"

	cargo_text="
├─ CARGO location : ${YELLOW}none${BLACK}${BLACK}
├─ CARGO_CLI      : ${YELLOW}none${BLACK}
├─ STAGE_IN_PATH  : ${YELLOW}none${BLACK}
└─ ADDRESS_CARGO  : ${YELLOW}none${BLACK}"
local gkfs_status="${YELLOW}OFF${BLACK}"
local cargo_status="${YELLOW}OFF${BLACK}"
fi

echo -e " 

${JIT} ${GREEN}Settings      
##################${BLACK}
${GREEN}Setup${BLACK}
├─ Logs dir       : ${BLUE}${LOG_DIR}${BLACK}
├─ PWD            : ${BLUE}$(pwd)${BLACK}
├─ FTIO           : ${ftio_status}
├─ GKFS           : ${gkfs_status}
├─ CARGO          : ${cargo_status}
├─ CLUSTER        : ${BLUE}${CLUSTER}${BLACK}
├─ Total NODES    : ${BLUE}${NODES}${BLACK}
├─ APP NODES      : ${BLUE}${APP_NODES}${BLACK}
├─ FTIO NODES     : ${BLUE}1${BLACK}
├─ PROCS          : ${BLUE}${PROCS}${BLACK}
├─ MAX_TIME       : ${BLUE}${MAX_TIME}${BLACK}
└─ Job ID         : ${BLUE}${JIT_ID}${BLACK}

${GREEN}FTIO${BLACK}${ftio_text}

${GREEN}Gekko${BLACK}${gkfs_text}

${GREEN} CARGO${BLACK}${cargo_text}

${GREEN}APP${BLACK}
├─ PRECALL        : ${BLUE}${PRECALL}${BLACK}
├─ APP_CALL       : ${BLUE}${APP_CALL}${BLACK}
├─ # NODES        : ${BLUE}${APP_NODES}${BLACK}
└─ APP NODES      : ${BLUE}${APP_NODES_COMMAND##'--nodelist='}${BLACK}
${GREEN}##################${BLACK}

"
}

function elapsed_time(){
	local name="$1"
	local start=$2
	local end=$3
	local runtime=$(echo  "${end} - ${start}" | bc | awk '{printf "%f\n", $0}')
	local runtime_formated=$(format_time ${runtime})
	echo -e "\n\n${BLUE}############${JIT}${BLUE}##############\n# ${name}\n# time: ${GREEN}${runtime_formated} ${BLUE}\n# ${GREEN}${runtime}${BLUE} seconds\n##############################${BLACK}\n\n" | tee -a ${LOG_DIR}/time.log
}

function log_dir(){
	if [[ -z "${LOG_DIR}" ]]; then
		LOG_DIR="logs_nodes${NODES}_Jobid${JIT_ID}"
	fi
	mkdir -p ${LOG_DIR}
	LOG_DIR=$(realpath ${LOG_DIR})
}

function execute(){
	local exec_call=$1
	
	if [[ $# -eq 2 ]];	then
		echo -e "${JIT}${YELLOW} >> $2 ${BLACK}"
	fi

	echo -e "${JIT}${CYAN} >> Executing: ${exec_call} ${BLACK}"
	eval " ${exec_call}"
}
