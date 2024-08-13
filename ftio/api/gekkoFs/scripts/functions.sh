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

function check_port() {

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

function allocate() {
	APP_NODES=1

	if [ "$CLUSTER" == true ]; then
		echo -e "\n${JIT}${GREEN} ####### Allocating resources${BLACK}"

		local call="salloc -N ${NODES} -t ${MAX_TIME} ${ALLOC_CALL_FLAGS}"

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
		scontrol show hostname $(squeue -j ${JIT_ID} -o "%N" | tail -n +2) >~/hostfile_mpi
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
			APP_NODES_COMMAND="--nodelist=$(echo ${NODES_ARR[@]/${FTIO_NODE}/} | tr ' ' ',')"
			SINGLE_NODE_COMMAND="--nodelist=${SINGLE_NODE}"

			APP_NODES=$((${NODES} - 1))
			sed -i "/${FTIO_NODE}/d" ~/hostfile_mpi
		fi

		echo -e "${JIT}${GREEN} >> JIT Job Id: ${JIT_ID} ${BLACK}"
		echo -e "${JIT}${GREEN} >> Allocated Nodes: "${#NODES_ARR[@]}" ${BLACK}"
		echo -e "${JIT}${GREEN} >> FTIO Node: ${FTIO_NODE} ${BLACK}"
		echo -e "${JIT}${GREEN} >> APP  Node command: ${APP_NODES_COMMAND} ${BLACK}"
		echo -e "${JIT}${GREEN} >> FTIO Node command: ${FTIO_NODE_COMMAND} ${BLACK}"
		echo -e "${JIT}${GREEN} >> cat ~/hostfile_mpi: \n$(cat ~/hostfile_mpi) ${BLACK}\n"
	else
		PROCS=${NODES}
	fi
}

# Start FTIO
function start_ftio() {

	if [ "$EXCLUDE_FTIO" == true ] || [ "${EXCLUDE_ALL}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping FTIO ${BLACK}"
		# Set relevant files using regex
		relevant_files true

		if [ "${EXCLUDE_CARGO}" == false ]; then
			# echo -e "${JIT}${YELLOW} Executing the calls bellow used later for staging out${BLACK}"
			call_0="srun --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${CARGO_CLI}/cargo_ftio --server ${CARGO_SERVER} --run"
			call_1="srun --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${CARGO_CLI}/ccp --server ${CARGO_SERVER} --input / --output ${STAGE_OUT_PATH} --if gekkofs --of parallel"
			execute "${call_0}"
			execute "${call_1}"
		fi
	else
		echo -e "\n${JIT}${GREEN} ####### Starting FTIO ${BLACK}"
		# Set relevant files using regex
		relevant_files true
		# set -x
		if [ "$CLUSTER" == true ]; then
			source ${FTIO_ACTIVATE}

			# One node is only for FTIO
			echo -e "${JIT}${CYAN} >> FTIO started on node ${FTIO_NODE}, remainng nodes for the application: ${APP_NODES} each with ${PROCS} processes ${BLACK}"
			echo -e "${JIT}${CYAN} >> FTIO is listening node is ${ADDRESS_FTIO}:${PORT} ${BLACK}"

			# call
			local call="srun --jobid=${JIT_ID} ${FTIO_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 predictor_jit  --zmq_address ${ADDRESS_FTIO} --zmq_port ${PORT} --cargo_cli ${CARGO_CLI} --cargo_server ${CARGO_SERVER} --cargo_out ${STAGE_OUT_PATH} "
		else
			#clean port
			check_port
			local call="predictor_jit  --zmq_address ${ADDRESS_FTIO} --zmq_port ${PORT} --cargo_cli ${CARGO_CLI} --cargo_server ${CARGO_SERVER} --cargo_out ${STAGE_OUT_PATH} "
			# 2>&1 | tee  ./ftio_${NODES}.txt
		fi
		# set -o xtrace
		execute "${call}"
		echo -e "\n\n"
	fi
}

# Start the Server
function start_geko_demon() {
	if [ "${EXCLUDE_DEMON}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping GKFS DEMON ${BLACK}"
	else
		echo -e "\n${JIT}${GREEN} ####### Starting GKFS DEOMON ${BLACK}"
		# creat host file
		create_hostfile
		# set -x
		if [ "$CLUSTER" == true ]; then
			# Display Demon
			call_0="srun --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} -N 1 --ntasks=1 mkdir -p ${GKFS_MNTDIR}"
			# EXCLUDE_PROXY=false

			if [ "$EXCLUDE_PROXY" == true ]; then
				# Demon call
				local call="srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${GKFS_DEMON}  -r ${GKFS_ROOTDIR} -m ${GKFS_MNTDIR} -H ${GKFS_HOSTFILE}  -c -l ib0 -P ofi+sockets -p ofi+verbs -L ib0"
			else
				# Demon call no proxy
				local call="srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${GKFS_DEMON}  -r ${GKFS_ROOTDIR} -m ${GKFS_MNTDIR} -H ${GKFS_HOSTFILE}  -c -l ib0 -P ofi+sockets"
			fi

		else
			call_0="mkdir -p ${GKFS_MNTDIR}"

			# Geko Demon call
			# local call="GKFS_DAEMON_LOG_LEVEL=info ${GKFS_DEMON} -r ${GKFS_ROOTDIR} -m ${GKFS_MNTDIR} -H ${GKFS_HOSTFILE} -p ofi+tcp"
			local call="GKFS_DAEMON_LOG_LEVEL=info ${GKFS_DEMON} -r ${GKFS_ROOTDIR} -m ${GKFS_MNTDIR} -H ${GKFS_HOSTFILE} -c -l lo -P ofi+tcp --proxy-listen lo --proxy-protocol ofi+tcp"
			#-c --auto-sm
		fi
		echo -e "${JIT}${CYAN} >> Creating Directory ${BLACK}"
		execute "${call_0}"
		echo -e "${JIT}${CYAN} >> Starting Demons ${BLACK}"
		execute "${call}"
		echo -e "\n\n"
	fi
}

function start_geko_proxy() {

	if [ "${EXCLUDE_PROXY}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping GKFS PROXY ${BLACK}"
	else
		echo -e "\n${JIT}${GREEN} ####### Starting GKFS PROXY ${BLACK}"
		if [ "$CLUSTER" == true ]; then
			# Proxy call
			local call="srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${GKFS_PROXY}  -H ${GKFS_HOSTFILE} -P ${GKFS_PROXYFILE} -p ofi+verbs"
			#
			# old
			# srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS} \
			# --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
			# ${GKFS_PROXY}  \
			# -H ${GKFS_HOSTFILE} -p ofi+verbs -P ${GKFS_PROXYFILE}
		else

			local call="${GKFS_PROXY} -H ${GKFS_HOSTFILE} -p ofi+tcp -P ${GKFS_PROXYFILE}"
		fi
		execute "${call}"
		echo -e "\n\n"
	fi
}

function start_cargo() {
	if [ "${EXCLUDE_CARGO}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping Cargo ${BLACK}"
	else
		echo -e "\n${JIT}${GREEN} ####### Starting Cargo ${BLACK}"
		# set -x
		if [ "$CLUSTER" == true ]; then

			# One instance per node
			local call="srun --export=LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LD_LIBRARY_PATH=${LD_LIBRARY_PATH} --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0  ${CARGO} --listen ofi+sockets://ib0:62000 -b 65536"
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
			# local call="mpiexec -np 4 --oversubscribe -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LD_LIBRARY_PATH=${LD_LIBRARY_PATH} taskset -c 11-14  ${CARGO} --listen ofi+tcp://127.0.0.1:62000 -b 65536 "
			local call="mpiexec -np 2 --oversubscribe -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LD_LIBRARY_PATH=${LD_LIBRARY_PATH} ${CARGO} --listen ofi+tcp://127.0.0.1:62000 -b 65536 "
		fi
		execute "${call}"
		echo -e "\n\n"
	fi
}

# Application call
function start_application() {
	echo -e "\n${JIT}${GREEN} ####### Executing Application ${BLACK}"
	
	check_setup

	if [ "$CLUSTER" == true ]; then

		# without FTIO
		#? [--stag in (si)--]               [--stag out (so)--]
		#?              [---APP---]
		# with FTIO
		#? [--stag in--]   [so]  [so] ... [so]
		#?              [---APP---]

		# with srun
		# local call="srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS}  --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 --export=ALL,LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LD_LIBRARY_PATH=${LD_LIBRARY_PATH},LD_PRELOAD=${GKFS_INTERCEPT},LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE},LIBGKFS_ENABLE_METRICS=on,LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT} ${APP_CALL}"

		#original:
		# local call="srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS}  --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 --export=ALL,LD_PRELOAD=${GKFS_INTERCEPT},LIBGKFS_LOG=errors,LIBGKFS_LOG_OUTPUT=~/tarraf_gkfs_client.log,LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE},LIBGKFS_ENABLE_METRICS=on,LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT},LD_LIBRARY_PATH=${LD_LIBRARY_PATH}  ${APP_CALL}"

		# local call="LIBGKFS_LOG=errors,warnings LIBGKFS_LOG_OUTPUT=~/tarraf_gkfs_client.log LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE} LIBGKFS_ENABLE_METRICS=on LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT} LD_PRELOAD=${GKFS_INTERCEPT}  srun --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES} --ntasks=${APP_NODES} --cpus-per-task=${PROCS}  --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 --export=LD_LIBRARY_PATH=${LD_LIBRARY_PATH} ${APP_CALL}"

		# app call
		if [ "${EXCLUDE_ALL}" == true ]; then
			# run without jit tools
			local call="${PRECALL} mpiexec -np ${PROCS} --oversubscribe --hostfile ~/hostfile_mpi --map-by node ${APP_CALL}"
		elif [ "${EXCLUDE_FTIO}" == true ]; then
			# run without FTIO
			local call="${PRECALL} mpiexec -np ${PROCS} --oversubscribe --hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=errors -x LD_PRELOAD=${GKFS_INTERCEPT} -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE} ${APP_CALL}"
		else
			# run with jit tools
			local call="${PRECALL} mpiexec -np ${PROCS} --oversubscribe --hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=errors -x LIBGKFS_ENABLE_METRICS=on -x LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT} -x LD_PRELOAD=${GKFS_INTERCEPT} -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE} ${APP_CALL}"
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

	else
		# app call
		if [ "${EXCLUDE_ALL}" == true ]; then
			local call=" ${PRECALL} mpiexec -np ${PROCS} --oversubscribe ${APP_CALL}"
		elif [ "${EXCLUDE_FTIO}" == true ]; then
			local call=" ${PRECALL} mpiexec -np ${PROCS} --oversubscribe -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LIBGKFS_LOG=none -x LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE} -x LD_PRELOAD=${GKFS_INTERCEPT} ${APP_CALL}"
		else
			local call=" ${PRECALL} mpiexec -np ${PROCS} --oversubscribe -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LIBGKFS_LOG=none -x LIBGKFS_ENABLE_METRICS=on -x LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT} -x LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE} -x LD_PRELOAD=${GKFS_INTERCEPT} ${APP_CALL}"
		fi
	fi

	start=$(date +%s.%N | {
		read -r secs_nanos
		secs=${secs_nanos%.*}
		nanos=${secs_nanos#*.}
		printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null
	})
	execute " ${call}"
	end=$(date +%s.%N | {
		read -r secs_nanos
		secs=${secs_nanos%.*}
		nanos=${secs_nanos#*.}
		printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null
	})
	FINISH=true

	elapsed_time "Application finished" ${start} ${end}
	local call="echo '${end} - ${start}' | bc"
	APP_TIME=$(eval "$call" )
}

function stage_out() {

	if [ "${EXCLUDE_ALL}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping Stage out ${BLACK}"
	else
		echo -e "\n${JIT}${YELLOW} ####### Stagin out ${BLACK}"

		local files=$(LD_PRELOAD=${GKFS_INTERCEPT} LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} ls ${GKFS_MNTDIR})
		echo -e "${JIT}${CYAN} >> geko_ls ${GKFS_MNTDIR}: \n${files} ${BLACK}\n"

		reset_relevant_files

		# stage out call on any compute node
		if [ "$CLUSTER" == true ]; then
			local call="srun --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${CARGO_CLI}/cargo_ftio --server ${CARGO_SERVER} --run"
		else
			local call="mpiexec -np 1 --oversubscribe ${CARGO_CLI}/cargo_ftio --server ${CARGO_SERVER} --run"
		fi

		start=$(date +%s.%N | {
			read -r secs_nanos
			secs=${secs_nanos%.*}
			nanos=${secs_nanos#*.}
			printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null
		})
		execute_and_wait_stage_out "${call}" ${CYAN} " > Stage out: ${call}" "Transfer finished for"
		end=$(date +%s.%N | {
			read -r secs_nanos
			secs=${secs_nanos%.*}
			nanos=${secs_nanos#*.}
			printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null
		})
		elapsed_time "Stage out" ${start} ${end}
		local call="echo '${end} - ${start}' | bc"
		STAGE_OUT_TIME=$(eval "$call" )
		
		# set ignored files to default again
		relevant_files
	fi
}

function stage_in() {
	if [ "${EXCLUDE_ALL}" == true ]; then
		echo -e "\n${JIT}${YELLOW} ####### Skipping Stage in ${BLACK}"
	else
		echo -e "\n${JIT}${YELLOW} ####### Stagin in ${BLACK}"

		# stage in call on any compute node
		if [ "$CLUSTER" == true ]; then

			local call="srun --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${CARGO_CLI}/ccp --server ${CARGO_SERVER} --output / --input ${STAGE_IN_PATH} --of gekkofs --if parallel"
			# local call="LD_PRELOAD=${GKFS_INTERCEPT}  LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE}  cp -r ${STAGE_IN_PATH}/* ${GKFS_MNTDIR}"
			# local call="srun --export=LD_LIBRARY_PATH=${LD_LIBRARY_PATH},LD_PRELOAD=${GKFS_INTERCEPT},LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} --jobid=${JIT_ID} ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 /usr/bin/cp -r ${STAGE_IN_PATH}/* ${GKFS_MNTDIR}"
		else
			local call="mpiexec -np 1 --oversubscribe ${CARGO_CLI}/ccp --server ${CARGO_SERVER} --output / --input ${STAGE_IN_PATH}  --of gekkofs --if parallel"
		fi

		start=$(date +%s.%N | {
			read -r secs_nanos
			secs=${secs_nanos%.*}
			nanos=${secs_nanos#*.}
			printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null
		})
		execute_and_wait_msg "${call}" ${CYAN} " > Stage in: ${call}" "retval: CARGO_SUCCESS, status: {state: completed"
		end=$(date +%s.%N | {
			read -r secs_nanos
			secs=${secs_nanos%.*}
			nanos=${secs_nanos#*.}
			printf "%d.%09d\n" "$secs" "$nanos" 2>/dev/null
		})
		elapsed_time "Stage in" ${start} ${end}
		local call="echo '${end} - ${start}' | bc"
		STAGE_IN_TIME=$(eval "$call" )

		local files=$(LD_PRELOAD=${GKFS_INTERCEPT} LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} ls ${GKFS_MNTDIR})
		echo -e "${JIT}${CYAN} >> geko_ls ${GKFS_MNTDIR}:${BLACK} \n${files} ${BLACK}\n"
	fi
}

#precall
function pre_call() {
	if [ -n "${PRE_APP_CALL}" ]; then
		echo -e "\n${JIT}${GREEN} ####### Pre-application Call ${BLACK}"
		execute "${PRE_APP_CALL}"
	fi
}

# post call
function post_call() {
	if [ -n "${POST_APP_CALL}" ]; then
		echo -e "\n${JIT}${GREEN} ####### Post-application Call ${BLACK}"
		execute " ${POST_APP_CALL}"
	fi
}

function soft_kill() {
	echo -e "\n${JIT}${GREEN} ####### Soft kill ${BLACK}"

	if [ "$EXCLUDE_FTIO" == false ]; then
		shut_down "FTIO" ${FTIO_PID} &
		echo -e "${JIT}${CYAN} >> killed FTIO ${BLACK}"
	fi
	if [ "$EXCLUDE_DEMON" == false ]; then
		shut_down "GEKKO" ${GEKKO_DEMON_PID} &
		echo -e "${JIT}${CYAN} >> killed GEKKO DEMON ${BLACK}"
	fi
	if [ "$EXCLUDE_PROXY" == false ]; then
		shut_down "GEKKO" ${GEKKO_PROXY_PID} &
		echo -e "${JIT}${CYAN} >> killed GEKKO PROXY ${BLACK}"
	fi
	if [ "$EXCLUDE_CARGO" == false ]; then
		shut_down "CARGO" ${CARGO_PID} &
		echo -e "${JIT}${CYAN} >> killed CARGO ${BLACK}"
	fi
}

function hard_kill() {
	if [ "$CLUSTER" == true ]; then
		echo -e "\n${JIT}${GREEN} ####### Hard kill ${BLACK}"
		scancel ${JIT_ID} || true
	else
		echo -e "\n${JIT}${GREEN} ####### Hard kill ${BLACK}"
		kill $(ps -aux | grep ${GKFS_DEMON} | grep -v grep | awk '{print $2}') || true
		kill $(ps -aux | grep ${GKFS_PROXY} | grep -v grep | awk '{print $2}') || true
		kill $(ps -aux | grep ${CARGO} | grep -v grep | awk '{print $2}') || true
		kill $(ps -aux | grep "$(dirname "$FTIO_ACTIVATE")/predictor_jit" | grep -v grep | awk '{print $2}') || true
	fi
}
# Function to handle SIGINT (Ctrl+C)
function handle_sigint() {
	echo "${JIT} > Keyboard interrupt detected. Exiting script."
	soft_kill
	scancle ${JIT_ID}
	exit 0
}

function check_finish() {
	# Set trap to handle SIGINT
	trap 'handle_sigint' SIGINT

	while :; do
		if [ "$FINISH" == true ]; then
			echo "${JIT} > FINISH flag is true. Exiting script in 10 sec."
			sleep 10
			exit 0
		fi
	done
}

function error_usage() {
	echo -e "Usage: $0 [OPTION]... \n
	-a | --address: X.X.X.X <string>
		default: ${BLACK}${ADDRESS_FTIO}${BLACK}
		Address where FTIO is executed. On a cluster, this is found 
		automatically by determining the address of node where FTIO 
		runs.

	-p | --port: XXXX <int>
		default: ${BLACK}${PORT}${BLACK}
		port for FTIO and GekkoFS.

	-n | --nodes: X <int>
		default: ${BLACK}${NODES}${BLACK}
		number of nodes to run the setup. in cluster mode, FTIO is 
		executed on a single node, while the rest (including the
		application) get X-1 nodes.

	-t | --max-time: X <int>
		default: ${BLACK}${MAX_TIME}${BLACK}
		max time for the execution of the setup in minutes.
	
	-l |--log-name: <str>
		default: Autoset to number of nodes and job id
		if provided, sets the name of the directory were the logs are

	-e | --execlude: <str>,<str>,...,<str>
		deafult: ftio
		if this flag is provided, the setup is executed without the tool(s).
		supported options include: ftio, demon, proxy, geko (demon + proxy), 
		cargo, and all (same as -x).

	-x | --exclude-all
		deafult: ${EXCLUDE_ALL}
		if this flag is provided, the setup is executed without FTIO, 
		GekkoFs, and Cargo.

	-i | install-location: full_path <str>
		deafult: ${BLACK}${INSTALL_LOCATION}${BLACK}
		installs everyting in the provided directory.

\n---- exit ----
    "
}

abort() {
	echo >&2 '
***************
*** ABORTED ***
***************
'
	echo "An error occurred. Exiting..." >&2
	exit 1
}

function install_all() {
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

	# clone cargo:EXCLUDE_FTIO=false
EXCLUDE_CARGO=false
EXCLUDE_DEMON=false
EXCLUDE_PROXY=false
	cd ${INSTALL_LOCATION}
	git clone https://storage.bsc.es/gitlab/hpc/cargo.git
	cd cargo
	# git checkout rnou/fmt10
	git checkout marc/nek5000 #fixes slow Cargo and verbosity
	cd ..

	# build cargo
	cd cargo && mkdir build && cd build
	vim +332 ../src/master.cpp #adapt regex path
	cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=${INSTALL_LOCATION}/iodeps -DCMAKE_INSTALL_PREFIX=${INSTALL_LOCATION}/iodeps ..
	# cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=${INSTALL_LOCATION}/iodeps -DCMAKE_INSTALL_PREFIX=${INSTALL_LOCATION}/iodeps 	-DGKFS_BUILD_TESTS=ON  -DCARGO_TRANSPORT_LIBRARY:STRING=libfabric ..

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

}
function parse_options() {
	# Define the options
	OPTIONS=a:p:n:t:l:i:e:xh
	LONGOPTS=address:,port:,nodes:,max-time:,log-name:,install-location:,exclude:,exclude-all,help

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
		-a | --address)
			ADDRESS_FTIO="$2"
			shift 2
			;;
		-p | --port)
			PORT="$2"
			shift 2
			;;
		-n | --nodes)
			NODES="$2"
			shift 2
			;;
		-t | --max-time)
			MAX_TIME="$2"
			shift 2
			;;
		-l | --log-name)
			LOG_DIR="$2"
			shift 2
			;;
		-i | --install-location)
			INSTALL_LOCATION="$2"
			install_all
			shift 2
			;;
		-e | --exclude)
			# Check if argument is provided or not
			echo -e "${JIT} ${GREEN}>>${YELLOW} Excluding: "
			if [[ -z "$2" || "$2" == -* ]]; then
				# Default to 'ftio' if no string is passed
				EXCLUDE_FTIO=true
				echo -e "- ftio "
				[[ "$2" == -* ]] && shift || shift 2
			else
				IFS=',' read -ra EXCLUDES <<< "$2"
				for exclude in "${EXCLUDES[@]}"; do
					case "$exclude" in
					ftio)
						EXCLUDE_FTIO=true
						echo -e "- ftio "
						;;
					cargo)
						EXCLUDE_CARGO=true
						echo -e "- cargo "
						;;
					gkfs)
						EXCLUDE_DEMON=true
						EXCLUDE_PROXY=true
						echo -e "- gkfs "
						;;
					demon)
						EXCLUDE_DEMON=true
						echo -e "- demon "
						;;
					proxy)
						EXCLUDE_PROXY=true
						echo -e "- proxy "
						;;
					all)
						EXCLUDE_ALL=true
						echo -e "- all "
						;;
					*)
						echo -e "${JIT} >>${RED}Invalid exclude option: $exclude ${BLACK}" >&2
						exit 1
						;;
					esac
				done
				shift 2
			fi
			echo -e "${BLACK}"
			;;
		-x | --exclude-all)
			EXCLUDE_ALL=true
			shift
			;;
		-h | --help)
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


function find_time() {

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

function shut_down() {
	local name=$1
	local PID=$2
	echo "Shutting down ${name} with PID ${PID}"
	if [[ -n ${PID} ]]; then
		# kill -s SIGINT ${PID} &
		kill ${PID}

		# wait works only for local
		if [ "$CLUSTER" == true ]; then
			wait ${PID}
		fi
	fi
}

function get_id() {
	trueIdid=$(squeue | grep "APPXGEKKO" | awk '{print $(1) }')
	return $trueIdid
}

function info() {
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
	until [ $(($(wc -l "${GKFS_HOSTFILE}" 2>/dev/null | awk '{print $1}') + 0)) -eq "${nodes}" ]; do
		sleep 2
		server_wait_cnt=$((server_wait_cnt + 1))
		if [ ${server_wait_cnt} -gt 600 ]; then
			echo "Server failed to start. Exiting ..."
			exit 1
		fi
	done
}

function create_hostfile() {
	echo -e "${JIT}${CYAN} >> Cleaning Hostfile: ${GKFS_HOSTFILE} ${BLACK}"
	rm -f ${GKFS_HOSTFILE} || echo -e "${BLUE}>> No hostfile found ${BLACK}"

	# echo -e "${CYAN}>> Creating Hostfile: ${GKFS_HOSTFILE} ${BLACK}"
	# touch ${GKFS_HOSTFILE}
	# for i in "${NODES_ARR[@]::${#NODES_ARR[@]}-1}"; do #exclude last element as this is FTIO_NODE
	# 	echo "cpu$i" >> ${GKFS_HOSTFILE}
	# done
}

function check_error_free() {
	if [ $? -eq 0 ]; then
		echo -e "${JIT}${GREEN} >> $1 successful ${BLACK}"
	else
		echo -e "${JIT}${RED} >> $1 failed! Exiting ${BLACK}<<<" >&2
		exit 1
	fi
}

function progress() {
	Animationflag=0
	trueID=$(get_id)
	status=$(squeue | grep $trueId | awk '{print $5 }' | tail -1)
	job_nodes=$(squeue | grep $trueId | awk '{print $(9) }' | tail -1)
	time_limit=$(squeue | grep $trueId | awk '{print $(7) }' | tail -1)
	while [[ $status != "C" ]] && [[ $status != "F" ]] && [[ $status != "S" ]] && [[ ! -z $status ]]; do
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
			sleep $(echo "($MAX_TIME)/20" | bc -l)
		fi

		status=$(squeue | grep $trueId | awk '{print $5 }' | tail -1)
	done

	echo -e "${GREEN}\n  ---- Simulation complete ----${BLACK}"

	time=$(squeue | grep $trueId | awk '{print $(6) }' | tail -1)
	if [[ -z "$time" ]]; then
		time=$(squeue | awk '{print $(6) }' | tail -1)
	fi
	echo -e "${BLUE}  Finished run with $job_nodes nodes in $time / $time_limit${BLACK}"
}

function get_address_ftio() {
	# get Address and port
	echo -e "\n${BLUE}####### Getting FTIO ADDRESS ${BLACK}"
	if [ "$CLUSTER" == true ]; then
		local call="srun --jobid=${JIT_ID} ${FTIO_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ip addr | grep ib0 | awk '{print \$2}'| cut -d'/' -f1 | tail -1"
		echo -e "${JIT}${CYAN} >> Executing: ${call} ${BLACK}"
		ADDRESS_FTIO=$(eval " ${call}")
		# ADDRESS_FTIO=$(eval " ${call}" | awk '{print $NF}')
	else
		echo "using default address"
	fi

	echo -e "${JIT} ${GREEN}>> ADDRESS_FTIO: ${ADDRESS_FTIO}${BLACK}"
}

function get_address_cargo() {
	echo -e "\n${BLUE}####### Getting Cargo ADDRESS ${BLACK}"
	if [ "$CLUSTER" == true ]; then
		local call="srun --jobid=${JIT_ID}  ${SINGLE_NODE_COMMAND} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ip addr | grep ib0 | awk '{print \$2}'| cut -d'/' -f1 | tail -1"
		echo -e "${JIT}${CYAN} >> Executing: ${call} ${BLACK}"
		ADDRESS_CARGO=$(eval " ${call}")
		CARGO_SERVER="ofi+sockets://${ADDRESS_CARGO}:62000"
	else
		CARGO_SERVER="ofi+tcp://${ADDRESS_CARGO}:62000"
	fi

	echo -e "${JIT} ${GREEN}>> ADDRESS_CARGO: ${ADDRESS_CARGO}${BLACK}"
	echo -e "${JIT} ${GREEN}>> CARGO_SERVER:  ${CARGO_SERVER}${BLACK}"
}

function format_time() {
	local input_time="$1"
	local int_time="${input_time%.*}"
	local nanos="${input_time#*.}"

	local h=$(bc <<<"${int_time}/3600")
	local m=$(bc <<<"(${int_time}%3600)/60")
	local s=$(bc <<<"${int_time}%60")
	local out=$(printf "%02d:%02d:%02d.%s\n" $h $m $s $nanos)
	echo "${out}"
}

function print_settings() {

	local ftio_status="${GREEN}ON${BLACK}"
	local gkfs_demon_status="${GREEN}ON${BLACK}"
	local gkfs_proxy_status="${GREEN}ON${BLACK}"
	local cargo_status="${GREEN}ON${BLACK}"

	local ftio_text="
├─ FTIO_ACTIVATE  : ${BLACK}${FTIO_ACTIVATE}${BLACK}
├─ ADDRESS_FTIO   : ${BLACK}${ADDRESS_FTIO}${BLACK}
├─ PORT           : ${BLACK}${PORT}${BLACK}
├─ # NODES        : ${BLACK}1${BLACK}
└─ FTIO NODE      : ${BLACK}${FTIO_NODE_COMMAND##'--nodelist='}${BLACK}"

	local gkfs_demon_text="
├─ GKFS_DEMON     : ${BLACK}${GKFS_DEMON}${BLACK}
├─ GKFS_INTERCEPT : ${BLACK}${GKFS_INTERCEPT}${BLACK}
├─ GKFS_MNTDIR    : ${BLACK}${GKFS_MNTDIR}${BLACK}
├─ GKFS_ROOTDIR   : ${BLACK}${GKFS_ROOTDIR}${BLACK}
├─ GKFS_HOSTFILE  : ${BLACK}${GKFS_HOSTFILE}${BLACK}"
	local gkfs_proxy_text="
├─ GKFS_PROXY     : ${BLACK}${GKFS_PROXY}${BLACK}
└─ GKFS_PROXYFILE : ${BLACK}${GKFS_PROXYFILE}${BLACK}"

	local cargo_text="
├─ CARGO          : ${BLACK}${CARGO}${BLACK}${BLACK}
├─ CARGO_CLI      : ${BLACK}${CARGO_CLI}${BLACK}
├─ STAGE_IN_PATH  : ${BLACK}${STAGE_IN_PATH}${BLACK}
└─ ADDRESS_CARGO  : ${BLACK}${ADDRESS_CARGO}${BLACK}"

	if [ "$EXCLUDE_FTIO" == true ] ; then
		ftio_text="
├─ FTIO_ACTIVATE  : ${YELLOW}none${BLACK}
├─ ADDRESS_FTIO   : ${YELLOW}none${BLACK}
├─ PORT           : ${YELLOW}none${BLACK}
├─ # NODES        : ${YELLOW}none${BLACK}
└─ FTIO NODE      : ${YELLOW}none${BLACK}"

		ftio_status="${YELLOW}OFF${BLACK}"
	fi

	if [ "${EXCLUDE_DEMON}" == true ]; then
		gkfs_demon_text="
├─ GKFS_DEMON     : ${YELLOW}none${BLACK}
├─ GKFS_INTERCEPT : ${YELLOW}none${BLACK}
├─ GKFS_MNTDIR    : ${YELLOW}none${BLACK}
├─ GKFS_ROOTDIR   : ${YELLOW}none${BLACK}
├─ GKFS_HOSTFILE  : ${YELLOW}none${BLACK}"
	gkfs_demon_status="${YELLOW}OFF${BLACK}"
	fi 

	if [ "${EXCLUDE_PROXY}" == true ]; then
		gkfs_proxy_text="
├─ GKFS_PROXY     : ${YELLOW}none${BLACK}
└─ GKFS_PROXYFILE : ${YELLOW}none${BLACK}"
		gkfs_proxy_status="${YELLOW}OFF${BLACK}"
	fi

	if [ "${EXCLUDE_CARGO}" == true ]; then
		cargo_text="
├─ CARGO location : ${YELLOW}none${BLACK}${BLACK}
├─ CARGO_CLI      : ${YELLOW}none${BLACK}
├─ STAGE_IN_PATH  : ${YELLOW}none${BLACK}
└─ ADDRESS_CARGO  : ${YELLOW}none${BLACK}"
		cargo_status="${YELLOW}OFF${BLACK}"
	fi

	echo -e " 

${JIT} ${GREEN}Settings      
##################${BLACK}
${GREEN}Setup${BLACK}
├─ Logs dir       : ${BLACK}${LOG_DIR}${BLACK}
├─ PWD            : ${BLACK}$(pwd)${BLACK}
├─ FTIO           : ${ftio_status}
├─ GKFS DEMON     : ${gkfs_demon_status}
├─ GKFS PROXY     : ${gkfs_proxy_status}
├─ CARGO          : ${cargo_status}
├─ CLUSTER        : ${BLACK}${CLUSTER}${BLACK}
├─ Total NODES    : ${BLACK}${NODES}${BLACK}
├─ APP NODES      : ${BLACK}${APP_NODES}${BLACK}
├─ FTIO NODES     : ${BLACK}1${BLACK}
├─ PROCS          : ${BLACK}${PROCS}${BLACK}
├─ MAX_TIME       : ${BLACK}${MAX_TIME}${BLACK}
└─ Job ID         : ${BLACK}${JIT_ID}${BLACK}

${GREEN}FTIO${BLACK}${ftio_text}

${GREEN}Gekko${BLACK}${gkfs_demon_text}${gkfs_proxy_text}

${GREEN} CARGO${BLACK}${cargo_text}

${GREEN}APP${BLACK}
├─ PRECALL        : ${BLACK}${PRECALL}${BLACK}
├─ APP_CALL       : ${BLACK}${APP_CALL}${BLACK}
├─ # NODES        : ${BLACK}${APP_NODES}${BLACK}
└─ APP NODES      : ${BLACK}${APP_NODES_COMMAND##'--nodelist='}${BLACK}
${GREEN}##################${BLACK}

"
}

function elapsed_time() {
	local name="$1"
	local start=$2
	local end=$3
	local runtime=$(echo "${end} - ${start}" | bc | awk '{printf "%f\n", $0}')
	local runtime_formated=$(format_time ${runtime})
	echo -e "\n\n${BLUE}############${JIT}${BLUE}##############\n# ${name}\n# time:${BLACK} ${runtime_formated} ${BLUE}\n#${BLACK} ${runtime} ${BLUE}seconds\n##############################${BLACK}\n\n" | tee -a ${LOG_DIR}/time.log

}

function log_dir() {
	if [[ -z "${LOG_DIR}" ]]; then
		LOG_DIR="logs_nodes${NODES}_Jobid${JIT_ID}"
	fi
	mkdir -p ${LOG_DIR}
	LOG_DIR=$(realpath ${LOG_DIR})
}

function execute() {
	local exec_call=$1

	if [[ $# -eq 2 ]]; then
		echo -e "${JIT}${CYAN} >> $2 ${BLACK}"
	elif [[ $# -eq 3 ]]; then
		echo -e "${JIT}$2$3${BLACK}"
	else
		echo -e "${JIT}${CYAN} >> Executing: ${exec_call} ${BLACK}"
	fi

	eval "${exec_call}"
}

function execute_and_wait_msg() {
	local exec_call="$1"
	# message to stop the command at
	local message="$4"
	#save the size of the cargo log file
	local last_pos=$(stat -c %s "${LOG_DIR}/cargo.log")
	echo -e "${JIT}"$2""$3"${BLACK}"
	eval " ${call}"
	# id=$(eval " ${call}")
	# id=$(echo $id  | grep -oP '(?<=server replied with: )\d+')

	while true; do
		current_pos=$(stat -c %s "${LOG_DIR}/cargo.log")
		if ((current_pos > last_pos)); then
			LAST_LINE=$(tail -n 1 "${LOG_DIR}/cargo.log")
			if [[ "$LAST_LINE" == *"$message"* ]]; then
				echo -e "${JIT}${CYAN} >> End of transfer detected ${BLACK}"
				break
			fi
		fi
	done
}

function execute_and_wait_stage_out() {
	local exec_call="$1"
	# message to stop the command at
	message="$4"
	#save the size of the cargo log file

	# Store the current position in the log file
	local start_lines=$(wc -l <"${LOG_DIR}/cargo.log")

	echo -e "${JIT}"$2""$3"${BLACK}"
	eval " ${call}"

	echo -e "${JIT}${CYAN} >> Waiting for  '${message}' ${BLACK}"

	while true; do
		current_lines=$(wc -l <"${LOG_DIR}/cargo.log")
		if ((current_lines > start_lines)); then
			n_lines=$((${current_lines} - ${start_lines}))
			files=$(tail -n ${n_lines} "${LOG_DIR}/cargo.log")
			if [[ "${files}" == *"${message}"* ]]; then
				echo -e "${JIT}${CYAN} >> End of transfer detected ${BLACK}"
				break
			fi
		fi
	done

	files=$(echo "${files}" | grep "${message}")
	if [[ "${files}" == *"Transfer finished for []"* ]]; then
		return
	else
		local last_file=$(echo "${files}" | grep -oP '(?<=path: ").*?(?=")' | tail -1)
		echo -e "${JIT}${CYAN} >> Waiting for deletion of ${last_file} ${BLACK}"
		while true; do
			LAST_LINE=$(tail -n 1 "${LOG_DIR}/cargo.log")
			if [[ "$LAST_LINE" == *"Deleting ${last_file}"* ]]; then
				echo -e "${JIT}${CYAN} >> End of call detected ${BLACK}"
				break
			fi
		done
	fi
}

function wait_msg() {
	local log="$1"
	local message="$2"
	echo -e "${JIT}${CYAN} >> Waiting for detection of ${message} ${BLACK}"
	local last_pos=$(stat -c %s "${log}")
	while true; do
		current_pos=$(stat -c %s "${log}")
		if ((current_pos > last_pos)); then
			LAST_LINE=$(tail -n 1 "${log}")
			if [[ "$LAST_LINE" == *"$message"* ]]; then
				echo -e "${JIT}${CYAN} >> End of transfer detected ${BLACK}"
				break
			fi
		fi
	done
}

function cancel_jit_jobs() {
	if [ -n "$(hostname | grep 'cpu\|mogon')" ]; then
		# Get the list of job IDs with the name "JIT"
		jit_jobs=$(squeue --me --name=JIT --format=%A | tail -n +2)

		if [ -z "$jit_jobs" ]; then
			return
		fi

		echo -e "${JIT}${YELLOW} >> The following jobs with the name 'JIT' were found:\n $jit_jobs"

		# Prompt the user to confirm cancellation
		read -p "Do you want to cancel all 'JIT' jobs? (yes/no): " confirmation

		if [[ "$confirmation" == "yes" || "$confirmation" == "y" || "$confirmation" == "ye" ]]; then
			for job_id in $jit_jobs; do
				scancel "$job_id"
				echo -e "${JIT}${CYAN} >> Cancelled job ID $job_id"
			done
			echo -e "${JIT}${GREEN} >> All 'JIT' jobs have been cancelled."
		else
			echo -e "${JIT}${YELLOW} >> No jobs were cancelled."
		fi
	fi
}

function get_pid() {
	local name=$1
	local pid=$2
	if [ "$CLUSTER" == true ]; then
		pid=$(ps aux | grep "srun" | grep "${JIT_ID}" | grep "$1" | grep -v grep | tail -1 | awk '{print $2}')
	fi

	if [[ "${name}" == "${CARGO}" ]]; then
		CARGO_PID=${pid}
		echo -e "${JIT}${GREEN} CARGO PID: ${CARGO_PID} ${BLACK}"
	elif [[ "${name}" == "${GKFS_DEMON}" ]]; then
		GEKKO_DEMON_PID=${pid}
		echo -e "${JIT}${GREEN} GEKKO_DEMON PID: ${GEKKO_DEMON_PID} ${BLACK}"
	elif [[ "${name}" == "${GKFS_PROXY}" ]]; then
		GEKKO_PROXY_PID=${pid}
		echo -e "${JIT}${GREEN} GEKKO_PROXY PID: ${GEKKO_PROXY_PID} ${BLACK}"
	elif  [[ "${name}" == "FTIO" ]] || [[ "${name}" == "predictor_jit" ]] ; then
		FTIO_PID=${pid}
		echo -e "${JIT}${GREEN} FTIO PID: ${FTIO_PID} ${BLACK}"
	fi
}

function relevant_files() {
	# if [ "$CLUSTER" == true ]; then
		if [[ $# -eq 1 ]]; then
			echo -e "${JIT}${CYAN} >> Setting up ignored files${BLACK}"
		fi

		local call="echo -e '${REGEX_MATCH}' > ${REGEX_FILE}"
		if [[ $# -eq 1 ]]; then
			execute "${call}"
		else
			eval "${call}"
		fi

		if [[ $# -eq 1 ]]; then
			echo -e "${JIT}${CYAN} >> Files that match ${REGEX_MATCH} are ignored ${BLACK}"
		fi
		echo -e "${JIT}${CYAN} >> cat ${REGEX_FILE}: \n$(cat ${REGEX_FILE}) ${BLACK}\n"
	# fi

}

function reset_relevant_files() {

	if [ "$CLUSTER" == true ]; then
		echo -e "${JIT}${CYAN} >> Reseting ignored files${BLACK}"
		local call="echo -e  '.*' > ${REGEX_FILE}"
		execute "${call}"
		# echo -e "${JIT}${CYAN} >> cat ${REGEX_FILE}: \n$(cat ${REGEX_FILE}) ${BLACK}\n"
	fi

}

function total_time() {
	local tot_time=$(cat ${LOG_DIR}/time.log | grep "seconds" | awk {'print $2'} | awk '{s+=$1} END {print s}')
	echo -e "\n${JIT}${GREEN} >>\n       App time: ${APP_TIME}\n  Stage in time: ${STAGE_IN_TIME}\n Stage out time: ${STAGE_OUT_TIME}\n---------------- ${BLACK}"
	echo -e "${JIT} --> Total Time: ${tot_time}${BLACK}\n" | tee -a ${LOG_DIR}/time.log
}


function check_setup(){
	# check settings
	if [ "${EXCLUDE_ALL}" == false ]; then
		echo -e "${JIT}${CYAN} >> MPI hostfile:${BLACK}\n$(cat ~/hostfile_mpi) ${BLACK}\n"
		echo -e "${JIT}${CYAN} >> Gekko hostfile:${BLACK}\n$(cat ${GKFS_HOSTFILE}) ${BLACK}\n"
		local files=$(LD_PRELOAD=${GKFS_INTERCEPT} LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} ls ${GKFS_MNTDIR})
		echo -e "${JIT}${CYAN} >> geko_ls ${GKFS_MNTDIR}:${BLACK}\n${files} ${BLACK}\n"
		
		# echo -e "${JIT}${CYAN} >> statx:${BLACK}\n"
		# mpiexec -np ${PROCS} --oversubscribe --hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=errors -x LD_PRELOAD=${GKFS_INTERCEPT} -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE} /home/tarrafah/nhr-admire/tarraf/FTIO/ftio/api/gekkoFs/scripts/test.sh
		
		# echo -e "${JIT}${CYAN} >> SESSION.NAME:${BLACK}\n$(cat /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/SESSION.NAME) ${BLACK}\n"
	
		# Tersting
		local files2=$(srun --export=LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LD_LIBRARY_PATH=${LD_LIBRARY_PATH},LD_PRELOAD=${GKFS_INTERCEPT} --jobid=${JIT_ID} ${APP_NODES_COMMAND} --disable-status -N ${APP_NODES}  --ntasks=1 --cpus-per-task=1 --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0  /usr/bin/ls ${GKFS_MNTDIR} )
		echo -e "${JIT}${CYAN} >> srun ls ${GKFS_MNTDIR}:${BLACK}\n${files2} ${BLACK}\n"
		# local files3=$(mpiexec -np 1 --oversubscribe --hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=errors -x LIBGKFS_ENABLE_METRICS=on -x LIBGKFS_METRICS_IP_PORT=${ADDRESS_FTIO}:${PORT} -x LD_PRELOAD=${GKFS_INTERCEPT} -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE} /usr/bin/ls ${GKFS_MNTDIR} )
		# echo -e "${JIT}${CYAN} >> mpirun ls ${GKFS_MNTDIR}:${BLACK}\n${files3} ${BLACK}\n"
	fi

	sleep 1
}

function set_flags(){
	if [ "${EXCLUDE_ALL}" == true ]; then
		EXCLUDE_FTIO=true
		EXCLUDE_CARGO=true
		EXCLUDE_DEMON=true
		EXCLUDE_PROXY=true
		APP_TIME="0"
		STAGE_IN_TIME="0"
		STAGE_OUT_TIME="0"
	fi
}

