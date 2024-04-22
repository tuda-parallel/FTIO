#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# get defaullts values 
source ${SCRIPT_DIR}/default.sh

#get needed functions 
source ${SCRIPT_DIR}/functions.sh

#parse  options
parse_options "$@"

# check port and address are free
check_port

# Only proceed if PORT is free
if [ $? -eq 0 ]; then # Check return code of is_port_in_use function (0 for free PORT)
	
	echo "Starting commands..."
	
	## old
	# start_geko &
	# start_cargo & 
	
	# start_application 
	# check_finish
	
	# 1. Allocate resources
	allocate
	
	# 2. Start FTIO
	start_ftio &
	FTIO_PID=$!

	# 3. Start Gekko Server
	start_geko &
	GEKKO_PID=$!

	# 4. Start Cargo Server
	start_cargo &
	CARGO_PID=$!

	# 5. Start application with Gekko intercept
	start_application
	
	shut_down "FTIO" ${FTIO_PID}
	shut_down "GEKKO" ${GEKKO_PID}
	shut_down "CARGO" ${CARGO_PID}

	echo "Commands completed."
	exit 0
fi

exit 1


