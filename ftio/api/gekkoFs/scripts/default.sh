#!/bin/bash

BLACK="\033[0m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"
JIT="\033[1;32m[JIT]\033[0m"
FINISH=false #set using export in
JOB_ID=0
JOB_NAME="JIT"
FTIO_NODE=""
ALL_NODES=""
APP_NODES_COMMAND=""
FTIO_NODE_COMMAND=""
SINGLE_NODE_COMMAND=""
LOG_DIR=""
APP_TIME=""
STAGE_IN_TIME=""
STAGE_OUT_TIME=""
GEKKO_DEMON_LOG=""
GEKKO_DEMON_ERR=""
GEKKO_PROXY_LOG=""
GEKKO_PROXY_ERR=""
GEKKO_CLIENT_LOG=""
CARGO_LOG=""
CARGO_ERR=""
FTIO_LOG=""
FTIO_ERR=""
APP_LOG=""
APP_ERR=""
STATIC_ALLOCATION=false
SET_TASKS_AFFINITY=true
TASK_SET_0=""
TASK_SET_1=""
echo -e "\n\n${GREEN}################ ${JIT} ${GREEN}################${BLACK}\n"

# by default FTIO is included in the setup
# Default values
EXCLUDE_FTIO=false
EXCLUDE_CARGO=false
EXCLUDE_DEMON=false
EXCLUDE_PROXY=true
EXCLUDE_ALL=false
DRY_RUN=false
VERBOSE=false
SKIP_CONFIRM=false

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
PROCS_LIST=${PROCS_LIST:-"64"}
PROCS_APP=${PROCS_APP:"-64"}
PROCS_DEMON=${PROCS_DEMON:"-64"}
PROCS_PROXY=${PROCS_PROXY:"64"}
PROCS_CARGO=${PROCS_CARGO:"-2"}
PROCS_FTIO=${PROCS_FTIO:"-128"}
OMP_THREADS=${OMP_THREADS:"-4"}


# Set default procs
if [ "$CLUSTER" = true ]; then
	PROCS_PROXY=$((PROCS / 2))
	PROCS_DEMON=$((PROCS / 2))
	PROCS_CARGO=2
	PROCS_FTIO=$PROCS
	PROCS_APP=$((PROCS / 2))
else
	PROCS=10
	PROCS_DEMON=1
	PROCS_PROXY=1
	PROCS_CARGO=2
	PROCS_FTIO=1
	PROCS_APP=$PROCS
fi