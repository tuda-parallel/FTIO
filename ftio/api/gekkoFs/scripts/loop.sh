#! /bin/bash

#------------------------------------------------------------------------------------------------------------
# Settings
#------------------------------------------------------------------------------------------------------------

# Executable name
EXECUTABLE="jit.sh"


# Nodes
nodes=(1 2 4 8 16) # 256)


#------------------------------------------------------------------------------------------------------------
# load defaults
#------------------------------------------------------------------------------------------------------------
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source ${SCRIPT_DIR}/default.sh

#------------------------------------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------------------------------------
echo -e "${GREEN}\n--------------------   Loop   -------------------\n${BLACK}Executable name: ${BLUE}${EXECUTABLE}\n${BLACK}\n\n "
echo -e "Enter a number great than 0 to run a single run.\nA number bellow 0 will launch a code specific for loop. "
echo -e "Suggestions:  ${YELLOW}1 2 4 8 16 ...${BLACK}"
read -p "Enter number of process: " n

#direct run
if [[ $n -gt 0 ]]; then
    ${SCRIPT_DIR}/default.sh 
#loop over nodes
else
    for NODES in ${nodes[@]}; do
		info
		NODES=$n
		MAX_TIME=$(find_time $NODES)
        ${SCRIPT_DIR}/${EXECUTABLE} -n ${NODES}  -t ${MAX_TIME} &
		progress
    done
fi

echo -e "${GREEN}\n--------------------       done       -------------------\n${BLACK}"
