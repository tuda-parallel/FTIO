#!/bin/bash
#SBATCH -J ior
##SBATCH --mail-type=END
#SBATCH -e %x.err
#SBATCH -o %x.out
#SBATCH -n 1536
#SBATCH --mem-per-cpu=3800   
#SBATCH -t 00:10:00

export LD_PRELOAD=./libtmio.so  
srun ./ior  -N ${SLURM_NPROCS} -t 2m -b 10m -s 2 -i 8 -a MPIIO -c

