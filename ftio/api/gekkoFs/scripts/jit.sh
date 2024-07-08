#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# get defaullts values 
source ${SCRIPT_DIR}/default.sh

#get needed functions 
source ${SCRIPT_DIR}/functions.sh

#parse  options
parse_options "$@"

if [ -z "$SCRIPT" ]
then 
    script log.txt bash -c "$0 $*"
    exit 0
fi
# check port and address are free
# Fixme: Move the line bellow to FTIO command
# check_port

# Only proceed if PORT is free
if [ $? -eq 0 ]; then # Check return code of is_port_in_use function (0 for free PORT)
	
	
	# 1. Allocate resources
	allocate
	# 1.1 Check allocation was successful
	check_error_free "Allocation"
	
	#1.2 get the address
	ADDRESS=$(get_address)
	
	# 1.3 create (clean) hostfile 
	create_hostfile

	# 2. Start Gekko Server (Demon)
	start_geko_demon &
	GEKKO_PID=$!
	sleep 5
	start_geko_proxy
	sleep 15
	
	# 3. Start Cargo Server
	start_cargo &
	CARGO_PID=$!
	sleep 15
	
	
	# 4. Start FTIO
	start_ftio &
	FTIO_PID=$!
	sleep 12


	# 5. Start application with Gekko intercept
	start_application
	
	# 6. soft kill
	shut_down "FTIO" ${FTIO_PID}
	shut_down "GEKKO" ${GEKKO_PID}
	shut_down "CARGO" ${CARGO_PID}
	
	# 7. over kill
	scancel ${JIT_ID} || true 

	echo "Commands completed."
	exit 0
fi

exit 1


