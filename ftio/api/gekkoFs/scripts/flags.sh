###################
# ALLOC call
###################
# ALLOC_CALL_FLAGS="--overcommit --oversubscribe --partition parallel -A nhr-admire --job-name JIT --no-shell"
ALLOC_CALL_FLAGS=" --overcommit --oversubscribe --partition largemem -A nhr-admire --job-name JIT --no-shell"

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
#Gekko mount directory
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
# execute as ${PRCALL} ${Other_calls}
PRECALL="time"

###################
# APP call 
###################
# APP_CALL="/lustre/project/nhr-admire/tarraf/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
# APP_CALL="/lustre/project/nhr-admire/tarraf/HACC-IO/HACC_ASYNC_IO 1000000 ${GKFS_MNTDIR}/mpi"
APP_CALL="./nek5000"
# Pre call
PRE_APP_CALL="echo -e 'turbPipe\n${GKFS_MNTDIR}' > /lustre/project/nhr-admire/tarraf/admire/turbPipe/run_gkfs/SESSION.NAME"

if [ "$CLUSTER" = true ]; then
	# install location in case -i option is provided to the script
	install_location=${install_location:-"/beegfs/home/Shared/admire/JIT"}
fi

if [ "$CLUSTER" = false ]; then
	# install location used to find stuff 
	install_location=${install_location:-"/d/github/JIT"}
	# FTIO
	FTIO_ACTIVATE="/d/github/FTIO/.venv/bin/activate"
	# Gekko Demon
	GKFS_DEMON="${install_location}/iodeps/bin/gkfs_daemon"
	#Gekko intercept call
	GKFS_INTERCEPT="${install_location}/iodeps/lib/libgkfs_intercept.so"
	#Gekko mount directory
	GKFS_MNTDIR="/tmp/JIT/tarraf_gkfs_mountdir"
	#Gekko root directory
	GKFS_ROOTDIR="/tmp/JIT/tarraf_gkfs_rootdir"
	# Host file location
	GKFS_HOSTFILE="~/gkfs_hosts.txt"
	# Gekko Proxy
	GKFS_PROXY="${install_location}/gekkofs/build/src/proxy/gkfs_proxy"
	# Gekko Proxy file
	GKFS_PROXYFILE="/tmp/JIT/vef_gkfs_proxy.pid"
	# Cargo 
	CARGO="${install_location}/cargo/build/src/cargo"
	CARGO_CLI="${install_location}/cargo/build/cli"
	STAGE_IN_PATH="~/input"
	# App
	APP_CALL="${install_location}/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
	#APP_CALL="/lustre/project/nhr-admire/tarraf/HACC-IO/HACC_ASYNC_IO 1000000 ${GKFS_MNTDIR}/mpi"
	# Pre call
	PRE_APP_CALL=" "
fi 


