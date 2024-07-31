#!/bin/bash

BLACK="\033[0m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"
JIT="\033[1;32m[JIT]\033[0m"
FINISH=false #set using export in
JIT_ID=""
FTIO_NODE=""
ALL_NODES=""
APP_NODES_COMMAND=""
FTIO_NODE_COMMAND=""
SINGLE_NODE_COMMAND=""
LOG_DIR=""
echo -e "${GREEN}################ ${JIT} ################${BLACK}"

# by default FTIO is included in the setup
EXCLUDE_FTIO=false
# by default FTIO+CARFO+GKFS are included in the setup
EXCLUDE_ALL=false

# Set default values. Check if enviromental variables are set
# cluster or local mode?
CLUSTER=false
if [ -n "$(hostname | grep 'cpu\|mogon')" ]; then
	CLUSTER=true
	if [ -n "$(hostname | grep 'mogon')" ]; then
		echo -e "${RED} Execute this script on cpu nodes\n mpiexec has still some bugs${BLACK}"
	fi
fi
echo -e "${JIT}${GREEN} >> CLUSTER MODE: ${CLUSTER}${BLACK}"

ip=$(ip addr | grep ib0 | awk '{print $4}' | tail -1)

###################
# Common variables
###################
ADDRESS_FTIO=${ADDRESS_FTIO:-"127.0.0.1"} # usually obtained automatically before executing FTIO
ADDRESS_CARGO=${ADDRESS_CARGO:-"127.0.0.1"} # usually obtained automatically before executing FTIO
PORT=${PORT:-"5555"}
NODES=${NODES:-"2"}
PROCS=${PROCS:-"128"}
MAX_TIME=${MAX_TIME:-"30"}



# TODO: Bind sockets to CPU numactl --cpunodebind=0,1 --membind=0,1 (particular sockets are faster)


