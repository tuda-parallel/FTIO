#!/bin/bash

BLACK="\033[0m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"
FINISH=false #set using export in
JIT_ID=""
FTIO_NODE=""
ALL_NODES=""
EXCLUDE=""

echo -e "\n"
echo -e "${GREEN}---- Started Script ----${BLACK}"

# Set default values. Check if enviromental variables are set
# cluster or local mode?
CLUSTER=false
if [ -n "$(hostname | grep 'cpu\|mogon')" ]; then
	CLUSTER=true
fi
echo -e "${GREEN}> Cluster Mode: ${CLUSTER}${BLACK}"

ip=$(ip addr | grep ib0 | awk '{print $4}' | tail -1)

###################
# Common variables
###################
ADDRESS=${ADDRESS:-"127.0.0.1"} # usually obtained automatically before executing FTIO
PORT=${PORT:-"5555"}
NODES=${NODES:-"2"}
PROCS=${PROCS:-"16"}
MAX_TIME=${MAX_TIME:-"30"}

# import flags
source ${SCRIPT_DIR}/flags.sh

# TODO: Bind sockets to CPU numactl --cpunodebind=0,1 --membind=0,1 (particular sockets are faster)
# TODO: remove FTIO from node list and exlude it from others (see functions.sh)
# TODO: Gekko Proxy
