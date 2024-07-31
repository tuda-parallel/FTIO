###################
# ALLOC call
###################
# ALLOC_CALL_FLAGS="--overcommit --oversubscribe --partition parallel -A nhr-admire --job-name JIT --no-shell"
ALLOC_CALL_FLAGS=" --overcommit --oversubscribe --partition largemem -A nhr-admire --job-name JIT --no-shell --exclude=cpu0082"

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
GKFS_INTERCEPT=${GKFS_INTERCEPT:-"/lustre/project/nhr-admire/vef/deps/gekkofs_zmq_install/lib64/libgkfs_intercept.so"}
#Gekko mount directory. This is also used in in case Gekko is off
GKFS_MNTDIR=${GKFS_MNTDIR:-"/dev/shm/tarraf_gkfs_mountdir"}
#Gekko root directory
GKFS_ROOTDIR=${GKFS_ROOTDIR:-"/dev/shm/tarraf_gkfs_rootdir"}
# Host file location
GKFS_HOSTFILE="/lustre/project/nhr-admire/tarraf/gkfs_hosts.txt"
# Gekko Proxy
GKFS_PROXY=${GKFS_PROXY:-"/lustre/project/nhr-admire/vef/gekkofs/build/src/proxy/gkfs_proxy"}
# Gekko Proxy file
GKFS_PROXYFILE=${GKFS_PROXYFILE:-"/dev/shm/vef_gkfs_proxy.pid"}


###################
# CARGO variables
###################
CARGO=${CARGO:-"/lustre/project/nhr-admire/vef/cargo/build/src/cargo"}

###################
# Stag in/out variables
###################
CARGO_CLI=${CARGO_CLI:-"/lustre/project/nhr-admire/vef/cargo/build/cli"}
CARGO_SERVER=${CARGO_SERVER:-"ofi+sockets://127.0.0.1:62000"}
STAGE_OUT_PATH=${STAGE_OUT_PATH:-"/lustre/project/nhr-admire/tarraf/stage-out"}
STAGE_IN_PATH=${STAGE_IN_PATH:-"/lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/input"}
# STAGE_IN_PATH="/lustre/project/nhr-admire/tarraf/stage_in"
# TODO: pass this to FTIO
#STAGE_OUT_PATH="/lustre/project/nhr-admire/tarraf/stage-out"


###################
# Pre call 
###################
# execute as ${PRECALL} ${Other_calls} ..${APP_CALL}
PRECALL="time"


#######################
# Pre and Post App Call
#######################
# Application specific calls executed before the actual run
if [ "${EXCLUDE_ALL}" = true ]; then
	PRE_APP_CALL="echo -e 'turbPipe\n/lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/input' > /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/SESSION.NAME"
	POST_APP_CALL="rm /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/input/*.f*"
else
	PRE_APP_CALL="echo -e 'turbPipe\n${GKFS_MNTDIR}' > /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/SESSION.NAME"
	POST_APP_CALL=""
fi


###################
# APP Call 
###################
# APP_CALL="/lustre/project/nhr-admire/tarraf/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
# APP_CALL="/lustre/project/nhr-admire/tarraf/HACC-IO/HACC_ASYNC_IO 1000000 ${GKFS_MNTDIR}/mpi"
APP_CALL="./nek5000"


###################
# Install Location
###################
# default install location in case -i option is provided to the script
if [ "$CLUSTER" = true ]; then
	INSTALL_LOCATION=${INSTALL_LOCATION:-"/beegfs/home/Shared/admire/JIT"}
fi


########################
# Local Machine Settings
########################
if [ "$CLUSTER" = false ]; then
	# install location used to find stuff 
	INSTALL_LOCATION=${INSTALL_LOCATION:-"/d/github/JIT"}
	# FTIO
	FTIO_ACTIVATE="/d/github/FTIO/.venv/bin/activate"
	# Gekko Demon
	GKFS_DEMON="${INSTALL_LOCATION}/iodeps/bin/gkfs_daemon"
	#Gekko intercept call
	GKFS_INTERCEPT="${INSTALL_LOCATION}/iodeps/lib/libgkfs_intercept.so"
	#Gekko mount directory
	GKFS_MNTDIR="/tmp/JIT/tarraf_gkfs_mountdir"
	#Gekko root directory
	GKFS_ROOTDIR="/tmp/JIT/tarraf_gkfs_rootdir"
	# Host file location
	GKFS_HOSTFILE="~/gkfs_hosts.txt"
	# Gekko Proxy
	GKFS_PROXY="${INSTALL_LOCATION}/gekkofs/build/src/proxy/gkfs_proxy"
	# Gekko Proxy file
	GKFS_PROXYFILE="/tmp/JIT/vef_gkfs_proxy.pid"
	# Cargo 
	CARGO="${INSTALL_LOCATION}/cargo/build/src/cargo"
	CARGO_CLI="${INSTALL_LOCATION}/cargo/build/cli"
	STAGE_IN_PATH="~/input"
	# App
	APP_CALL="${INSTALL_LOCATION}/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
	#APP_CALL="/lustre/project/nhr-admire/tarraf/HACC-IO/HACC_ASYNC_IO 1000000 ${GKFS_MNTDIR}/mpi"
	# Pre and post app calls
	PRE_APP_CALL=""
	POST_APP_CALL=""
fi 


