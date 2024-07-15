#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# get defaullts values 
source ${SCRIPT_DIR}/default.sh

#get needed functions 
source ${SCRIPT_DIR}/functions.sh


#parse  options
parse_options "$@"

# check port and address are free
# Fixme: Move the line bellow to FTIO command
# check_port


# Only proceed if PORT is free
if [ $? -eq 0 ]; then # Check return code of is_port_in_use function (0 for free PORT)
	
	
	# 1. Allocate resources
	allocate 

	# 1.1 Check allocation was successful
	check_error_free "Allocation"
	
	# 1.2 create folder for logs
	LOG_DIR="logs_n${NODES}_id${JIT_ID}"
	mkdir -p ${LOG_DIR}
	
	#1.3 get the address
	get_address
	
	# 1.4
	# print settings
	print_settings | tee ${LOG_DIR}/settings.log &

	
	# 1.5 create (clean) hostfile 
	create_hostfile

	# 2. Start Gekko Server (Demon)
	start_geko_demon &
	GEKKO_DEMON_PID=$!
	sleep 5
	start_geko_proxy &
	GEKKO_PROXY_PID=$!
	sleep 5
	
	# 3. Start Cargo Server
	start_cargo | tee ${LOG_DIR}/cargo.log &
	CARGO_PID=$!
	sleep 10
	
	# 4. Stage in
	stage_in | tee ${LOG_DIR}/stage_in.log 

	# 5. Start FTIO
	start_ftio | tee ${LOG_DIR}/ftio.log &
	FTIO_PID=$!
	sleep 12


	# 6. Start application with Gekko intercept
	start_application | tee ${LOG_DIR}/app.log 
	
	# 7. stage out
	stage_out | tee ${LOG_DIR}/stage_out.log 

	# 8. soft kill
	soft_kill
	sleep 5
	
	# 7. over kill
	hard_kill

	echo -e "${GREEN}------------- Commands completed ------------- ${BLACK}"
	exit 0
fi

exit 1


