#!/bin/bash

BLACK="\033[0m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"
FINISH=false #set using export in


echo -e "\n"
echo -e "${GREEN}Started Script${BLACK}"

# Set default ADDRESS and PORT
ADDRESS="127.0.0.1"
PORT=5555
PROCS=128

GEKKO_INERCEPT="/lustre/project/nhr-admire/vef/deps/gekkofs_zmq_install/lib64/libgkfs_intercept.so"
APP_CALL="ior -a POSIX -i 4 -o /tmp/gkfs_mountdir/iortest -t 128k -b 512m -F"
HOSTFILE="${HOME}/gkfs_hosts.txt"


error_usage(){
	echo -e "Usage: $0 -a X.X.X.X -p X -n X \n 
	-a: X.X.X.X (ip address <string>: ${BLUE}${ADDRESS}${BLACK}) 
	-p: XXXX (port <int>: ${BLUE}${PORT}${BLACK})
	-n: X (Processes <int>: ${BLUE}${PROCS}${BLACK})
\n---- exit ----
	"
}

# Parse command-line arguments using getopts
while getopts ":ha:p:n:" opt; do
	case $opt in
	a) ADDRESS="$OPTARG" ;;
	p) PORT="$OPTARG" ;;
	n) PROCS="$OPTARG" ;;
	h) 
		echo -e "${YELLOW}Help launch:  ${BLACK}" >&2
		error_usage $OPTARG
		exit 1;;
	\?)
		echo -e "${RED}Invalid option: -$1 ${BLACK}" >&2
		error_usage $OPTARG
		exit 1
		;;
	esac
done

# Shift positional arguments to remove processed flags and options
shift $((OPTIND - 1))

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

# Check if PORT is available
if is_port_in_use $PORT; then
	echo -e "${RED}Error: Port $PORT is already in use on $ADDRESS. Terminating existing process...${BLACK}"

	# Use ss command for potentially more reliable process identification (uncomment)
	# process_id=$(ss -tlpn | grep :"$PORT " | awk '{print $NF}')

	# Use netstat if ss is unavailable (uncomment)
	process_id=$(netstat -tlpn | grep :"$PORT " | awk '{print $7}')

	if [[ ! -z "$process_id" ]]; then
		echo -e "${YELLOW}Terminating process with PID: $process_id${BLACK}"
		kill "${process_id%/*}"
	else
		echo -e "${RED}Failed to identify process ID for PORT $PORT.${BLACK}"
	fi
	exit 1
else
	echo -e "${GREEN}Using $PORT on $ADDRESS.${BLACK}"
fi

# Start the Server
function start_geko() {

	echo -e "${GREEN}GKFS DEOMON started ${BLACK}\n"
	# Geko Demon call
	GKFS_DAEMON_LOG_PATH=/tmp/gkfs_daemon.log \
		GKFS_DAEMON_LOG_LEVEL=info \
		/lustre/project/nhr-admire/vef/deps/gekkofs_zmq_install/bin/gkfs_daemon \
		-r /dev/shm/gkfs_rootdir \
		-m /tmp/gkfs_mountdir \
		-c --auto-sm \
		-H ${HOSTFILE} 
}

# Application call
function start_application() {
	echo -e "${CYAN}Executing Application ${BLACK}\n"
	# application with Geko LD_PRELOAD
	mpiexec -np $PROCS --oversubscribe \
		-x LIBGKFS_HOSTS_FILE=${HOSTFILE} \
		-x LIBGKFS_LOG=none \
		-x LIBGKFS_ENABLE_METRICS=on \
		-x LIBGKFS_METRICS_IP_PORT=10.81.4.158:5555 \
		-x LD_PRELOAD=${GEKKO_INERCEPT} \
		${APP_CALL}
	echo -e "${CYAN}Application finished ${BLACK}\n"
	FINISH=true
}

function start_cargo() {
	echo -e "${GREEN}Starting Cargo ${BLACK}\n"
	# start Cargo
	mpiexec -np 2 --oversubscribe \
		--map-by node \
		-x LIBGKFS_HOS_FILE=${HOSTFILE} \
		--hostfile /lustre/project/nhr-admire/tarraf/hostfile \
		/lustre/project/nhr-admire/vef/cargo/build/src/cargo --listen \
		ofi+sockets://127.0.0.1:62000 \
		>> ./cargo_${PROCS}.txt
}


function start_ftio() {
	echo -e "${GREEN}Starting FTIO ${BLACK}\n"
	source /lustre/project/nhr-admire/tarraf/FTIO/.venv/bin/activate
	predictor_gekko \
	# 2>&1 | tee  ./ftio_${PROCS}.txt
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

# Only proceed if PORT is free
if [ $? -eq 0 ]; then # Check return code of is_port_in_use function (0 for free PORT)
	# Launch the commands in the background using "&"
	echo "Starting commands..."
	start_geko &
	start_cargo & 
	start_ftio > "ftio_${PROCS}.out" 2> "ftio_${PROCS}.err"
	start_application 

	# Print a message indicating successful launch
	echo "Commands launched in the background."

	check_finish
	# Wait for keyboard interrupt (Ctrl+C)
	# trap exit INT

	# Print a message upon successful execution (won't be reached due to Ctrl+C)
	echo "Commands completed."
	exit 0
fi

exit 1 # Indicate failure if PORT was occupied


