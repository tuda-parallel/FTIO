
# ? Job Allocation call
# ?####################
ALLOC_CALL_FLAGS="--overcommit --oversubscribe --partition largemem -A nhr-admire --job-name ${JOB_NAME} --no-shell --exclude=cpu0081,cpu0082,cpu0083,cpu0084"
# ALLOC_CALL_FLAGS=" --overcommit --oversubscribe --partition largemem -A nhr-admire --job-name JIT --no-shell --exclude=cpu0082"


# ? FTIO variables
# ?##################
FTIO_ACTIVATE=${FTIO_ACTIVATE:-"/lustre/project/nhr-admire/tarraf/FTIO/.venv/bin/activate"}


# ? Gekko variables
# ?####################
# Gekko Demon
GKFS_DEMON=${GKFS_DEMON:-"/lustre/project/nhr-admire/tarraf/deps/gekkofs_zmq_install/bin/gkfs_daemon"}
#Gekko intercept call
GKFS_INTERCEPT=${GKFS_INTERCEPT:-"/lustre/project/nhr-admire/tarraf/deps/gekkofs_zmq_install/lib64/libgkfs_intercept.so"}
#Gekko mount directory. This is also used in in case Gekko is off
GKFS_MNTDIR=${GKFS_MNTDIR:-"/dev/shm/tarraf_gkfs_mountdir"}
#Gekko root directory
GKFS_ROOTDIR=${GKFS_ROOTDIR:-"/dev/shm/tarraf_gkfs_rootdir"}
# Host file location
GKFS_HOSTFILE="/lustre/project/nhr-admire/tarraf/gkfs_hosts.txt"
# Gekko Proxy
GKFS_PROXY=${GKFS_PROXY:-"/lustre/project/nhr-admire/tarraf/gekkofs/build/src/proxy/gkfs_proxy"}
# Gekko Proxy file
GKFS_PROXYFILE=${GKFS_PROXYFILE:-"/dev/shm/tarraf_gkfs_proxy.pid"}



# ? CARGO variables
# ?##########################
CARGO=${CARGO:-"/lustre/project/nhr-admire/vef/cargo/build/src/cargo"}
CARGO_CLI=${CARGO_CLI:-"/lustre/project/nhr-admire/vef/cargo/build/cli"}
CARGO_SERVER=${CARGO_SERVER:-"ofi+sockets://127.0.0.1:62000"}


# ? APP settings
# ?##########################
# ****** app call ******
#  ├─ IOR
# APP="/lustre/project/nhr-admire/tarraf/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
# APP="/lustre/project/nhr-admire/tarraf/HACC-IO/HACC_ASYNC_IO 1000000 ${GKFS_MNTDIR}/mpi"
#  ├─ NEK5000
APP_CALL="./nek5000"
APP_DIR="/home/tarrafah/nhr-admire/shared/run_gkfs_marc"
#  └─ Wacom++
# APP_CALL="./wacommplusplus"
# APP_DIR="/lustre/project/nhr-admire/tarraf/wacommplusplus/build"

# ****** pre and post app call ******
# Application specific calls executed before the actual run.
# > ${PRE_APP_CALL}
# > cd APP_DIR && mpiexec ${some flags} ..${APP_CALL}
# > ${POST_APP_CALL}
# ├─ Nek5000
if [[ "$APP_CALL" == *"nek"* ]]; then
    if [ "$EXCLUDE_ALL" == true ]; then
        PRE_APP_CALL="echo -e 'turbPipe\n${APP_DIR}/input' > ${APP_DIR}/SESSION.NAME"
        POST_APP_CALL="rm ${APP_DIR}/input/*.f* || echo true"
    else
        PRE_APP_CALL="echo -e 'turbPipe\n${GKFS_MNTDIR}' > ${APP_DIR}/SESSION.NAME"
        POST_APP_CALL=""
    fi
# ├─ Wacom++
elif [[ "$APP_CALL" == *"wacom"* ]]; then
    if [ "$EXCLUDE_ALL" == true ]; then
        # In case a previous simulation fails
        PRE_APP_CALL="export OMP_NUM_THREADS=${OMP_THREADS}; ln -sf ${APP_DIR}/wacomm.pfs.json ${APP_DIR}/wacomm.json"
        POST_APP_CALL=""
    else
        PRE_APP_CALL="export OMP_NUM_THREADS=${OMP_THREADS}; ln -sf ${APP_DIR}/wacomm.gkfs.json ${APP_DIR}/wacomm.json"
        POST_APP_CALL="ln -sf ${APP_DIR}/wacomm.pfs.json ${APP_DIR}/wacomm.json"
    fi
# └─ Other
else
    PRE_APP_CALL=""
    POST_APP_CALL=""
fi

# ? Stage in/out
# ?##########################
# ├─ Nek5000
if [[ "$APP_CALL" == *"nek"* ]]; then
    STAGE_IN_PATH="${APP_DIR}/input"
    STAGE_OUT_PATH="/lustre/project/nhr-admire/tarraf/stage-out"
# ├─ Wacom++
elif [[ "$APP_CALL" == *"wacom"* ]]; then
    STAGE_IN_PATH="${APP_DIR}/stage-in"
    STAGE_OUT_PATH="/lustre/project/nhr-admire/tarraf/stage-out"
# └─ Other
else
    STAGE_IN_PATH="${APP_DIR}/stage-in"
    STAGE_OUT_PATH="/lustre/project/nhr-admire/tarraf/stage-out"
fi

# ? Regex if needed
# ?##########################
REGEX_FILE="/lustre/project/nhr-admire/shared/nek_regex4cargo.txt"
# ├─ Nek5000
if [[ "$APP_CALL" == *"nek"* ]]; then
    # REGEX_MATCH="^/[a-zA-Z0-9]*turbPipe0\\.f\\d+"
	REGEX_MATCH="^/[a-zA-Z0-9]*turbPipe0\.f\d+"
# ├─ Wacom++
elif [[ "$APP_CALL" == *"wacom"* ]]; then
    REGEX_MATCH="^(\\/output|\\/results|\\/restart|\\/input)\\/[^\\/]+$"  # "^ocm3_d03_\\d+Z\d+\\.nc$"
# └─ Other
else
    REGEX_MATCH=""
fi





###################
# Install Location
###################
# default install location in case -i option is provided to the script
if [ "$CLUSTER" == true ]; then
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
	GKFS_HOSTFILE="${PWD}/gkfs_hosts.txt"
	# Gekko Proxy
	GKFS_PROXY="${INSTALL_LOCATION}/gekkofs/build/src/proxy/gkfs_proxy"
	# Gekko Proxy file
	GKFS_PROXYFILE="${INSTALL_LOCATION}/tarraf_gkfs_proxy.pid"
	# Cargo 
	CARGO="${INSTALL_LOCATION}/cargo/build/src/cargo"
	CARGO_CLI="${INSTALL_LOCATION}/cargo/build/cli"
	STAGE_IN_PATH="/tmp/input"
	STAGE_OUT_PATH="/tmp/output"
	
	# App
	# APP_CALL="${INSTALL_LOCATION}/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
	#APP_CALL="/lustre/project/nhr-admire/tarraf/HACC-IO/HACC_ASYNC_IO 1000000 ${GKFS_MNTDIR}/mpi"
	# Pre and post app calls
	PRE_APP_CALL=""
	POST_APP_CALL=""
	REGEX_FILE="${INSTALL_LOCATION}/nek_regex4cargo.txt"
	# REGEX_MATCH="^/turbPipe0\.f\d+$"
	REGEX_MATCH="^/[a-zA-Z0-9]*turbPipe0\.f\d+"
	

	#Nek5000
	APP_DIR="/d/benchmark/Nek5000/turbPipe/run/"
	APP_CALL="./nek5000"
	STAGE_IN_PATH="/d/benchmark/Nek5000/turbPipe/run/input"
	if [ "${EXCLUDE_ALL}" == true ]; then
		PRE_APP_CALL="echo -e 'turbPipe\n/d/benchmark/Nek5000/turbPipe/run/input' > /d/benchmark/Nek5000/turbPipe/run/SESSION.NAME"
		POST_APP_CALL="rm /d/benchmark/Nek5000/turbPipe/run/input/*.f*"
	else
		PRE_APP_CALL="echo -e 'turbPipe\n${GKFS_MNTDIR}' > /d/benchmark/Nek5000/turbPipe/run/SESSION.NAME"
		POST_APP_CALL="rm ${STAGE_OUT_PATH}/*.f*"
	fi
fi 


