
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
GKFS_INERCEPT=${GKFS_INERCEPT:-"/lustre/project/nhr-admire/vef/gekkofs/build/src/client/libgkfs_intercept.so"}
#Gekko mount directory
GKFS_MNTDIR=${GKFS_MNTDIR:-"/dev/shm/tarraf_gkfs_mountdir"}
#Gekko root directory
GKFS_ROOTDIR=${GKFS_ROOTDIR:-"/dev/shm/tarraf_gkfs_rootdir"}
# Host file location
GKFS_HOSTFILE="/lustre/project/nhr-admire/tarraf/gkfs_hosts.txt"
# Gekko Proxy
GKFS_PROXY=${GKFS_PROXY:-"/lustre/project/nhr-admire/vef/gekkofs/build/src/proxy/gkfs_proxy"}
# Gekko Proxy file
GKFS_PROXYFILE=${GKFS_PROXYFILE:-"
/dev/shm/vef_gkfs_proxy.pid"}


###################
# CARGO variables
###################
CARGO=${CARGO:-"/lustre/project/nhr-admire/vef/cargo/build/src/cargo"}


###################
# APP call 
###################
APP_CALL="/lustre/project/nhr-admire/tarraf/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"


# install location in case -i option is provided to the script
install_location=${install_location:-"/beegfs/home/Shared/admire/JIT"}






if [ "$CLUSTER" = false ]; then
	# install location used to find stuff 
	install_location=${install_location:-"/d/github/JIT"}
	
	FTIO_ACTIVATE=${FTIO_ACTIVATE:-"/d/github/FTIO/.venv/bin/activate"}
	# Gekko Demon
	GKFS_DEMON=${GKFS_DEMON:-"${install_location}/deps/gekkofs_zmq_install/bin/gkfs_daemon"}
	#Gekko intercept call
	GKFS_INERCEPT=${GKFS_INERCEPT:-"${install_location}/deps/gekkofs_zmq_install/lib64/libgkfs_intercept.so"}
	#Gekko mount directory
	GKFS_MNTDIR=${GKFS_MNTDIR:-"/tmp/JIT/tarraf_gkfs_mountdir"}
	#Gekko root directory
	GKFS_ROOTDIR=${GKFS_ROOTDIR:-"/tmp/JIT/tarraf_gkfs_rootdir"}
	# Host file location
	GKFS_HOSTFILE="~/gkfs_hosts.txt"
	# Gekko Proxy
	GKFS_PROXY=${GKFS_PROXY:-"${install_location}/gekkofs/build/src/proxy/gkfs_proxy"}
	# Gekko Proxy file
	GKFS_PROXYFILE=${GKFS_PROXYFILE:-"/tmp/JIT/vef_gkfs_proxy.pid"}
	# Cargo 
	CARGO=${CARGO:-"${install_location}/cargo/build/src/cargo"}
	APP_CALL="${install_location}/ior/src/ior -a POSIX -i 4 -o ${GKFS_MNTDIR}/iortest -t 128k -b 512m -F"
fi 