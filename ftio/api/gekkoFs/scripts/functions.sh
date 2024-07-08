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
		echo -e "\n${GREEN}####### Allocating resources FTIO ${BLACK}"
		call="${PRECALL} salloc -N ${NODES} -t ${MAX_TIME} --overcommit --oversubscribe --partition parallel -A nhr-admire --job-name JIT --no-shell"
		echo -e ">> Executing: ${CYAN} ${call} ${BLACK}"
        # salloc -N ${NODES} -t ${MAX_TIME} --overcommit --oversubscribe --partition parallel -A nhr-admire --job-name JIT --no-shell
		eval " ${call}"
		
		JIT_ID=$(squeue | grep "JIT" |awk '{print $(1)}' | tail -1)
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
		
        if [ "${#NODES_ARR[@]}" -gt "1" ]; then
            EXCLUDE="--exclude=${FTIO_NODE}"
			EXCLUDE_FTIO="--exclude=$(echo ${NODES_ARR[@]/${FTIO_NODE}} | tr ' ' ',' )"
			NODES=$((${NODES} - 1))
			sed  -i "/${FTIO_NODE}/d" ~/hostfile_mpi
        fi
        
        echo -e "${CYAN}> JIT Job Id: ${JIT_ID} ${BLACK}"
		echo -e "${CYAN}> Allocated Nodes: "${#NODES_ARR[@]}" ${BLACK}"
		echo -e "${CYAN}> Exclude command: ${EXCLUDE} ${BLACK}"
		echo -e "${CYAN}> FTIO Node: ${FTIO_NODE} ${BLACK}"
		echo -e "${YELLOW}> App Nodes: $(cat ~/hostfile_mpi) ${BLACK}\n"
    fi
}


# Start FTIO
function start_ftio() {
    echo -e "\n${GREEN}####### Starting FTIO ${BLACK}"
    # set -x
    if [ "$CLUSTER" = true ]; then
        source ${FTIO_ACTIVATE}
        
		# One node is only for FTIO
        echo -e "${CYAN}>> FTIO started on node ${FTIO_NODE}, remainng nodes for the application: ${NODES} each with ${PROCS} processes ${BLACK}"
		echo -e "${CYAN}>> FTIO is listening node is ${ADDRESS}:${PORT} ${BLACK}"

		# call
		call="${PRECALL} srun --jobid=${JIT_ID} ${EXCLUDE_FTIO} --disable-status -N 1 --ntasks=1 --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 predictor_jit  --zmq_address ${ADDRESS} --zmq_port ${PORT}"
		echo -e "${CYAN}>> Executing: ${call} ${BLACK}"
		eval " ${call}"
		#
		# old
		# srun --jobid=${JIT_ID} ${EXCLUDE_FTIO} --disable-status -N 1 \
		# --ntasks=1 --cpus-per-task=${PROCS} \
        # --ntasks-per-node=1 --overcommit --overlap \
		# --oversubscribe --mem=0 \
        # predictor_jit  --zmq_address ${ADDRESS} --zmq_port ${PORT}
		#
        # Change CARGO path in predictor_jit_zmq.py if needed

    else
        predictor_jit  > "ftio_${NODES}.out" 2> "ftio_${NODES}.err"
        # 2>&1 | tee  ./ftio_${NODES}.txt
    fi
    # set -o xtrace
	echo -e "\n\n"
}

# Start the Server
function start_geko_demon() {
	echo -e "\n${GREEN}####### Starting GKFS DEOMON ${BLACK}"
    # set -x
    if [ "$CLUSTER" = true ]; then
		# Display Demon
		echo -e "${BLUE}>> Creating directory ${GKFS_MNTDIR}${BLACK}"
		srun --jobid=${JIT_ID} mkdir -p ${GKFS_MNTDIR}
		
		# Demon call
		call="${PRECALL} srun --jobid=${JIT_ID} ${EXCLUDE} --disable-status -N ${NODES} --ntasks=${NODES} --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${GKFS_DEMON}  -r ${GKFS_ROOTDIR} -m ${GKFS_MNTDIR} -H ${GKFS_HOSTFILE}  -c -l ib0 -P ofi+sockets -p ofi+verbs -L ib0"
		echo -e "${CYAN}>> Executing: ${call} ${BLACK}"
		eval " ${call}"
        # #
		# # old
		# srun --jobid=${JIT_ID} ${EXCLUDE} --disable-status -N ${NODES} --ntasks=${NODES} --cpus-per-task=${PROCS} \
        # --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
        # ${GKFS_DEMON}  \
        # -r ${GKFS_ROOTDIR} \
        # -m ${GKFS_MNTDIR} \
        # -H ${GKFS_HOSTFILE}  -c -l ib0 \
		# -P ofi+sockets -p ofi+verbs -L ib0
    else
		mkdir -p /dev/shm/tarraf_gkfs_mountdir/
        # Geko Demon call
        GKFS_DAEMON_LOG_LEVEL=info \
        ${GKFS_DEMON} \
        -r ${GKFS_ROOTDIR} \
		-m ${GKFS_MNTDIR}\
        -c --auto-sm \
        -H ${GKFS_HOSTFILE}
    fi
    # set -o xtrace
	echo -e "\n\n"
}
function start_geko_proxy() {
	echo -e "\n${GREEN}####### Starting GKFS PROXY ${BLACK}"
    if [ "$CLUSTER" = true ]; then
		# Proxy call
		call="${PRECALL} srun --jobid=${JIT_ID} ${EXCLUDE} --disable-status -N ${NODES} --ntasks=${NODES} --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ${GKFS_PROXY}  -H ${GKFS_HOSTFILE} -p ofi+verbs -P ${GKFS_PROXYFILE}"
		echo -e "${CYAN}>> Executing: ${call} ${BLACK}"
		eval " ${call}"
		#
		# old
		# srun --jobid=${JIT_ID} ${EXCLUDE} --disable-status -N ${NODES} --ntasks=${NODES} --cpus-per-task=${PROCS} \
        # --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
        # ${GKFS_PROXY}  \
		# -H ${GKFS_HOSTFILE} -p ofi+verbs -P ${GKFS_PROXYFILE}
    else
		mkdir -p /dev/shm/tarraf_gkfs_mountdir/
        # Geko Proxy call
        ${GKFS_PROXY}  -H ${GKFS_HOSTFILE} -p ofi+verbs -P ${GKFS_PROXYFILE}
    fi
}


# Application call
function start_application() {
    echo -e "\n${GREEN}####### Executing application ${BLACK}"
    # set -x
    if [ "$CLUSTER" = true ]; then
		# display hostfile
		echo -e "${YELLOW}> Hostfile cotains: $(cat ~/hostfile_mpi) ${BLACK}\n"

		
		# with srun
        # srun --jobid=${JIT_ID} ${EXCLUDE} --disable-status -N ${NODES} --ntasks=${NODES} --cpus-per-task=${PROCS} \
        # --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 \
		# --export=LIBGKFS_LOG=errors,warnings,LIBGKFS_LOG_OUTPUT=/dev/shm/tarraf_gkfs_client.log,LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE},LIBGKFS_ENABLE_METRICS=on,LIBGKFS_METRICS_IP_PORT=${ADDRESS}:${PORT},LD_PRELOAD=${GKFS_INTERCEPT},LD_LIBRARY_PATH=${LD_LIBRARY_PATH} \
        # ${APP_CALL}

		# without FTIO
		#? [--stag in--]               [--stag out--]
		#?              [---nek5000---]
		# with FTIO
		#? [--stag in--]   [so]  [so] ... [so]
		#?              [---nek5000---]
		
		
		# app call
		call="${PRECALL} mpiexec -np ${PROCS} --oversubscribe --hostfile ~/hostfile_mpi --map-by node -x LIBGKFS_LOG=errors,warnings -x LIBGKFS_ENABLE_METRICS=on -x LIBGKFS_METRICS_IP_PORT=${ADDRESS}:${PORT} -x LD_PRELOAD=${GKFS_INTERCEPT} -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} -x LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE} taskset -c 0-63 ${APP_CALL}"
		echo -e "${CYAN}>> Executing: ${call} ${BLACK}"
		start=`date +%s.%N`
		eval " ${call}"
		end=`date +%s.%N`
		runtime=$((end-start))

		# run and measure App
		# ${PRECALL} mpiexec -np ${PROCS} --oversubscribe \
		# --hostfile ~/hostfile_mpi \
		# --map-by node -x LIBGKFS_LOG=errors,warnings \
		# -x LIBGKFS_ENABLE_METRICS=on \
		# -x LIBGKFS_METRICS_IP_PORT=${ADDRESS}:${PORT}\
		# -x LD_PRELOAD=${GKFS_INTERCEPT}\
		# -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE}\
		# -x LIBGKFS_PROXY_PID_FILE=${GKFS_PROXYFILE}\
		# taskset -c 0-63 \
		# ${APP_CALL}
		
		# measure stage-out

    else
        mpiexec -np $NODES --oversubscribe \
        -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} \
        -x LIBGKFS_LOG=none \
        -x LIBGKFS_ENABLE_METRICS=on \
        -x LIBGKFS_METRICS_IP_PORT=${ADDRESS}:${PORT} \
        -x LD_PRELOAD=${GKFS_INTERCEPT} \
        ${APP_CALL}
        echo -e "${CYAN}Application finished ${BLACK}\n"
    fi
    # set -o xtrace
    FINISH=true
	runtime_formated=$(format_time ${runtime})
	echo -e "\n\n${BLUE}#######################################\n# Application finished\n# time: ${GREEN}${runtime_formated} ${BLACK}\n# ${runtime} seconds passed\n#######################################${BLACK}\n\n"
}

function start_cargo() {
    echo -e "\n${GREEN}####### Starting Cargo ${BLACK}"
    # set -x
    if [ "$CLUSTER" = true ]; then
        
		# One instance per node
		call="${PRECALL} srun --export=LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LD_LIBRARY_PATH=${LD_LIBRARY_PATH} --jobid=${JIT_ID} ${EXCLUDE} --disable-status -N ${NODES} --ntasks=${NODES} --cpus-per-task=${PROCS} --ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0  ${CARGO} --listen ofi+sockets://127.0.0.1:62000"
		echo -e "${CYAN}>> Executing: ${call} ${BLACK}"
		eval " ${call}"
		#
		# old
        # srun --export=LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE},LD_LIBRARY_PATH=${LD_LIBRARY_PATH} \
		# --jobid=${JIT_ID} ${EXCLUDE} --disable-status -N ${NODES} \
		# --ntasks=${NODES} --cpus-per-task=${PROCS} \
        # --ntasks-per-node=1 --overcommit --overlap --oversubscribe \
		# --mem=0  ${CARGO} --listen ofi+sockets://127.0.0.1:62000 
    else
        mpiexec -np 2 --oversubscribe \
        --map-by node \
        -x LIBGKFS_HOSTS_FILE=${GKFS_HOSTFILE} \
        ${CARGO} --listen \
        ofi+sockets://127.0.0.1:62000 \
        >> ./cargo_${NODES}.txt
    fi
    # set -o xtrace
	echo -e "\n\n"
}

function stage_out() {
	echo -e "\n${GREEN}####### Stagin out ${BLACK}"
	
	# stage out call
	call="${PRCALL} ${CARGO_PATH}/cargo_ftio --server ofi+sockets://127.0.0.1:62000 --run"
	
	echo -e "${CYAN}> Satgging out: ${call} ${BLACK}"
	start=`date +%s.%N`
	eval " ${call}"
	end=`date +%s.%N`
	runtime=$((end-start))
	runtime_formated=$(format_time ${runtime})
	echo -e "\n\n${BLUE}#######################################\n# Stage out\n# time: ${GREEN}${runtime_formated} ${BLACK}\n# ${runtime} seconds" 
}

function stage_in() {
	echo -e "\n${GREEN}####### Stagin in ${BLACK}"
	
	# stage in call
	call="${PRCALL} ${CARGO_PATH}/ccp --server ofi+sockets://127.0.0.1:62000 --output / --input ${STAGE_IN_PATH} --of gekkofs --if parallel"
	
	echo -e "${CYAN}> Satgging in: ${call} ${BLACK}"
	start=`date +%s.%N`
	eval " ${call}"
	end=`date +%s.%N`
	runtime=$((end-start))
	runtime_formated=$(format_time ${runtime})
	echo -e "\n\n${BLUE}#######################################\n# Stage out\n# time: ${GREEN}${runtime_formated} ${BLACK}\n# ${runtime} seconds" 
}

# Function to handle SIGINT (Ctrl+C)
function handle_sigint {
    echo "Keyboard interrupt detected. Exiting script."
	scancle ${JIT_ID}
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
	-n: X (nodes <int>: ${BLUE}${NODES}${BLACK})
	-t: X (max time <int>: ${BLUE}${NODES}${BLACK})

	-i install everyting
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

	echo -e "${GREEN}>> Installation stated${BLACK}"
	echo -e "${GREEN}>>> Creating directory${BLACK}"
	mkdir -p ${install_location}

    # Clone GKFS
    echo -e "${GREEN}>>> Installing GEKKO${BLACK}"
    cd ${install_location}
    git clone --recurse-submodules https://storage.bsc.es/gitlab/hpc/gekkofs.git
    cd gekkofs
    # git checkout main fmt10
    git pull --recurse-submodules
	cd ..
    

	# Workaround for lib fabric
	# echo -e "${RED}>>> Work around for libfabric${BLACK}"
	# sed  -i '/\[\"libfabric/d' ${install_location}/gekkofs/scripts/profiles/latest/default_zmq.specs
	# sed  -i 's/\"libfabric\"//g' ${install_location}/gekkofs/scripts/profiles/latest/default_zmq.specs
    
    # Build GKFS
    gekkofs/scripts/gkfs_dep.sh -p default_zmq ${install_location}/iodeps/git ${install_location}/iodeps
	cd gekkofs && mkdir build && cd build
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=${install_location}/iodeps -DGKFS_BUILD_TESTS=OFF -DCMAKE_INSTALL_PREFIX=${install_location}/iodeps -DGKFS_ENABLE_CLIENT_METRICS=ON ..
    make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"	
    echo -e "${GREEN}>>> GEKKO installed${BLACK}"
    
    #Cardo DEPS: CEREAL
    echo -e "${GREEN}>>> Installing Cargo${BLACK}"
    cd ${install_location}
    git clone https://github.com/USCiLab/cereal
    cd cereal && mkdir build && cd build
    cmake -DCMAKE_PREFIX_PATH=${install_location}/iodeps -DCMAKE_INSTALL_PREFIX=${install_location}/iodeps ..
    make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
    
    #Cargo DEPS: THALLIUM
    cd ${install_location}
    git clone https://github.com/mochi-hpc/mochi-thallium
    cd mochi-thallium && mkdir build && cd build
	cmake -DCMAKE_PREFIX_PATH=${install_location}/iodeps -DCMAKE_INSTALL_PREFIX=${install_location}/iodeps ..    
    make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
    
    # clone cargo:
    cd ${install_location}
    git clone https://storage.bsc.es/gitlab/hpc/cargo.git
    cd cargo
    git checkout rnou/fmt10
	cd ..
    
    # build cargo
    cd cargo && mkdir build && cd build
	cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=${install_location}/iodeps -DCMAKE_INSTALL_PREFIX=${install_location}/iodeps ..
    make -j 4 install || echo -e "${RED}>>> Error encountered${BLACK}"
    # GekkoFS should be found in the cargo CMAKE configuration.
    echo -e "${GREEN}>>> Cargon installed${BLACK}"
    
    ## build FTIO:
    # echo -e "${GREEN}>>> Installing FTIO${BLACK}"
    # cd ${install_location}
    # git clone https://github.com/tuda-parallel/FTIO.git
    # ml lang/Python/3.10.8-GCCcore-12.2.0 || echo "skipping module load";
    # cd FTIO
    # # Install FTIO
    # make install  || echo -e "${RED}>>> Error encountered${BLACK}"
    # echo -e "${GREEN}>>> FTIO installed${BLACK}"
    
    #build IOR
	cd ${install_location}
	git clone https://github.com/hpc/ior.git
	cd ior 
	./bootstrap
	./configure
	make -j 4 #&& make -j 4 install 

	echo -e "${GREEN}>> Installation finished${BLACK}"
    echo -e "\n
	>> read to go <<
	call: ./jit.sh  -n NODES -t MAX_TIME 
    "
	trap : 0
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
	echo -e "${CYAN}>> Cleaning Hostfile: ${GKFS_HOSTFILE} ${BLACK}"
	rm -f ${GKFS_HOSTFILE} || echo -e "${BLUE}>> No Hostfile found ${BLACK}"
	
	# echo -e "${CYAN}>> Creating Hostfile: ${GKFS_HOSTFILE} ${BLACK}"
	# touch ${GKFS_HOSTFILE}
	# for i in "${NODES_ARR[@]::${#NODES_ARR[@]}-1}"; do #exclude last element as this is FTIO_NODE
   	# 	echo "cpu$i" >> ${GKFS_HOSTFILE}
	# done
}

function check_error_free(){
	if [ $? -eq 0 ] 
	then 
  		echo -e "${GREEN}$1 successful ${BLACK}"
	else 
  		echo -e ">>> ${RED}$1 failed! Exiting ${BLACK}<<<">&2 
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

function get_address(){
	# get Address and port
	if [ "$CLUSTER" = true ]; then
		out=$(srun --jobid=${JIT_ID} ${EXCLUDE_FTIO} --disable-status -N 1 --ntasks=1 --cpus-per-task=1 \
		--ntasks-per-node=1 --overcommit --overlap --oversubscribe --mem=0 ip addr | grep ib0 | awk '{print $2}'| cut -d'/' -f1 | tail -1)
	else
		out="$ADDRESS"
	fi 
	echo ${out}
}

function format_time() {
 h=$(bc <<< "${1}/3600")
 m=$(bc <<< "(${1}%3600)/60")
 s=$(bc <<< "${1}%60")
 out=$(printf "%02d:%02d:%05.2f\n" $h $m $s)
 
 echo ${out}
}