#!/bin/bash

BLACK="\033[0m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"
FINISH=false #set using export in


echo -e "\n"
echo -e "${GREEN}---- Started Script ----${BLACK}"

# Set default values. Check if enviromental variables are set
# cluster or local mode?
CLUSTER=false

###################
# Common variables
###################
ADDRESS=${ADDRESS:-"127.0.0.1"} 
PORT=${PORT:-"5555"}
NODES=${NODES:-"2"}
MAX_TIME=${MAX_TIME:-"30"}

###################
# FTIO variables
###################
FTIO_ACTIVATE=${FTIO_ACTIVATE:-"/lustre/project/nhr-admire/tarraf/FTIO/.venv/bin/activate"}

###################
# Gekko variables
###################
# Gekko Demon
GKFS_DEMON=${GKFS_DEMON:-"/lustre/project/nhr-admire/vef/deps/gekkofs_zmq_install/bin/gkfs_daemon"}
#Gekko intercept call
GKFS_INERCEPT=${GKFS_INERCEPT:-"/lustre/project/nhr-admire/vef/deps/gekkofs_zmq_install/lib64/libgkfs_intercept.so"}
#Gekko mount directory
GKFS_MNTDIR=${GKFS_MNTDIR:-"/dev/shm/tarraf_gkfs_mountdir"}
#Gekko root directory
GKFS_ROOTDIR=${GKFS_ROOTDIR:-"/dev/shm/tarraf_gkfs_rootdir"}
# Host file location
GKFS_HOSTFILE="${HOME}/gkfs_hosts.txt"
###################

CARGO=${CARGO:-"/lustre/project/nhr-admire/vef/cargo/build/src/cargo"}

# APP call 
APP_CALL="ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"

# install location in case -i option is provided to the script
install_location=${install_location:-"/beegfs/home/Shared/admire/JIT"}