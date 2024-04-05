#!/bin/bash

BLACK="\033[0m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"

echo -e "\n"
echo -e "${GREEN}Started Script \n ${BLACK}"

# Set default address and port
ADDRESS="127.0.0.1"
PORT=5555
PROCS=128

GEKKO_INERCEPT="/lustre/project/nhr-admire/vef/deps/gekkofs_zmq_install/lib64/libgkfs_intercept.so"
APP_CALL="ior -a POSIX -i 4 -o /tmp/gkfs_mountdir/iortest -t 128k -b 512m -F"
HOSTFILE="${HOME}/gkfs_hosts.txt"

#! parse input
# Define variables to store parsed arguments
address=$ADDRESS
port=$PORT

# Parse command-line arguments using getopts
while getopts ":a:$p:" opt; do
	case $opt in
	a) address="$OPTARG" ;;
	p) port="$OPTARG" ;;
	\?)
		echo "${RED}Invalid option: -$OPTARG $ ${BLACK}" >&2
		exit 1
		;;
	esac
done

# Shift positional arguments to remove processed flags and options
shift $((OPTIND - 1))

# # or
# # Check for arguments and assign defaults if missing
# if [ $# -eq 0 ]; then
#   echo "No address or port provided, using defaults: $ADDRESS:$PORT"
#   address=$ADDRESS
#   port=$PORT
# elif [ $# -eq 1 ]; then
#   # If only one argument provided, assume it's the port
#   echo "No address provided, using default: $ADDRESS. Using provided port: $1"
#   address=$ADDRESS
#   port=$1
# else
#   # Extract address and port from arguments
#   address=$1
#   port=$2
# fi

# Function to check if port is in use
function is_port_in_use() {
	local port_number=$1
	port_output=$(netstat -tlpn | grep ":$port_number ")
	if [[ ! -z "$port_output" ]]; then
		# Port is in use
		echo -e "${RED}Error: Port $port_number is already in use...${BLACK}"
	else
		# Port is free
		echo -e "${BLUE}Port $port_number is available.${BLACK}"
	fi
}

# Check if port is available
if is_port_in_use $port; then
	echo -e "${RED}Error: Port $port is already in use on $address. Terminating existing process...${BLACK}"

	# Use ss command for potentially more reliable process identification (uncomment)
	# process_id=$(ss -tlpn | grep :"$port " | awk '{print $NF}')

	# Use netstat if ss is unavailable (uncomment)
	process_id=$(netstat -tlpn | grep :"$port " | awk '{print $7}')

	if [[ ! -z "$process_id" ]]; then
		echo -e "${YELLOW}Terminating process with PID: $process_id${BLACK}"
		kill "${process_id%/*}"
	else
		echo "${RED}Failed to identify process ID for port $port.${BLACK}"
	fi
else
	echo "${GREEN}Port $port is available on $address.${BLACK}"
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


# Only proceed if port is free
if [ $? -eq 0 ]; then # Check return code of is_port_in_use function (0 for free port)
	# Launch the commands in the background using "&"
	echo "Starting commands..."
	start_geko &
	start_cargo & 
	start_ftio 
	start_application 

	# Print a message indicating successful launch
	echo "Commands launched in the background."

	# Wait for keyboard interrupt (Ctrl+C)
	trap exit INT

	# Print a message upon successful execution (won't be reached due to Ctrl+C)
	echo "Commands completed."
	exit 0
fi

exit 1 # Indicate failure if port was occupied
