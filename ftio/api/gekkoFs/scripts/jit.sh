#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# get defaullts values and functions
source ${SCRIPT_DIR}/default.sh
source ${SCRIPT_DIR}/functions.sh


# parse  options
parse_options "$@"

# import flags
source ${SCRIPT_DIR}/flags.sh


# handle kill
trap 'handle_sigint' SIGINT

#clean other jobs
cancel_jit_jobs
set_flags

# Only proceed if PORT is free
if [ $? -eq 0 ]; then # Check return code of is_port_in_use function (0 for free PORT)
	
	
	# 1. Allocate resources
	allocate 

	# 1.1 Check allocation was successful
	check_error_free "Allocation"
	
	# 1.2 create folder for logs
	log_dir
	
	#1.3 get the address
	get_address_ftio 
	get_address_cargo
	

	# 1.4
	# print settings
	print_settings | tee ${LOG_DIR}/settings.log 

	
	# 2. Start Gekko Server (Demon)
	start_geko_demon | tee ${LOG_DIR}/geko_demon.log &
	sleep $((${NODES}*1))
	get_pid ${GKFS_DEMON} $!
	start_geko_proxy | tee ${LOG_DIR}/geko_proxy.log&
	sleep $((${NODES}*3))
	get_pid ${GKFS_PROXY} $!
	
	# 3. Start Cargo Server
	start_cargo | tee ${LOG_DIR}/cargo.log &
	if [ "${EXCLUDE_ALL}" == false ]; then
		wait_msg "${LOG_DIR}/cargo.log" "Start up successful"
	fi
	sleep $((${NODES}*1))
	get_pid ${CARGO} $!
	
	# 4. Stage in
	stage_in | tee ${LOG_DIR}/stage_in.log 
	# sleep $((${NODES}*5))

	# 5. Start FTIO
	start_ftio | tee ${LOG_DIR}/ftio.log &
	# TODO: this can lead to a deadlock if wait_msg is reached after start_ftio was completed
	if [ "${EXCLUDE_ALL}" == false ]; then
		wait_msg "${LOG_DIR}/cargo.log" "retval: CARGO_SUCCESS, status: {state: completed"
	fi
	sleep $((${NODES}*2))
	get_pid "predictor_jit" $!

	# 6. pre- and application with Gekko intercept
	pre_call
	start_application | tee ${LOG_DIR}/app.log 
	
	# 7. stage out
	stage_out | tee ${LOG_DIR}/stage_out.log 
	
	# 8. Post call if exists
	post_call
	
	# 9. Display total time
	total_time

	# 10. soft kill
	soft_kill
	sleep 5
	
	# 11. over kill
	hard_kill

	echo -e "${GREEN}############### ${JIT} ${GREEN}completed ############### ${BLACK}"
	exit 0
fi

exit 1


