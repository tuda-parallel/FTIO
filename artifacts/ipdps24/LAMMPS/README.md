# LAMMPS With 3072 Ranks

Extract the tar archive lammps.tar.gz:
```sh
tar -xf lammps.tar.gz
```
The folder contains:
1. Tracing file generated with TMIO: lammps_3072.json
2. Input simulation file and sbatch script in case you want to repeat the experiment on your cluster

Alternatively, download and extract the file data.zip as described [here](/artifacts/ipdps24/README.md#extracting-the-data-set).
Once extracted, you can find the LAMMPS trace under `application_traces/LAMMPS`.

## Analyzing the provided trace file

[Install FTIO](https://github.com/tuda-parallel/FTIO#installation). To get the dominant frequency with `ftio` simply call:

```sh
ftio lammps_3072.json
```

<p align="right"><a href="#lammps-with-3072-ranks">⬆</a></p>

## Repeating the experiment on your cluster
First, install the required software on your cluster:
- [Install TMIO](https://github.com/tuda-parallel/TMIO#installation) 
- [Install FTIO](https://github.com/tuda-parallel/FTIO#installation) 
- [Install LAMMPS](https://docs.lammps.org/Install.html) with MPI suppoort

For this experiment, we executed LAMMPS on the Lichtenberg cluster with the following sbatch.sh script:
```sh
#!/bin/bash                                                                                                   
#SBATCH -J lammps
#SBATCH -e %x.err
#SBATCH -o %x.out
#SBATCH -n 3072
#SBATCH --mem-per-cpu=3800   
#SBATCH -t 00:10:00

export LD_PRELOAD=./libtmio.so  
srun ./lmp_mpi -in in.flow.pois
```
Adapt the sbatch script for your system.

The file `in.flow.pois` contains the following:
```sh
# 2-d LJ flow simulation
dimension	2
boundary	p s p

atom_style	atomic
neighbor	0.3 bin
neigh_modify	delay 5

# create geometry
lattice		hex 0.7
region		box block 0 1024 0 1024 -0.25 0.25
create_box	3 box
create_atoms	1 box

mass		1 1.0
mass		2 1.0
mass		3 1.0

# LJ potentials
pair_style	lj/cut 1.12246
pair_coeff	* * 1.0 1.0 1.12246

# define groups
region	     1 block INF INF INF 1.25 INF INF
group	     lower region 1
region	     2 block INF INF 8.75 INF INF INF
group	     upper region 2
group	     boundary union lower upper
group	     flow subtract all boundary

set	     group lower type 2
set	     group upper type 3

# initial velocities
compute	     mobile flow temp
velocity     flow create 1.0 482748 temp mobile
fix	     1 all nve
fix	     2 flow temp/rescale 200 1.0 1.0 0.02 1.0
fix_modify   2 temp mobile

# Poiseuille flow
velocity     boundary set 0.0 0.0 0.0
fix	     3 lower setforce 0.0 0.0 0.0
fix	     4 upper setforce 0.0 NULL 0.0
fix	     5 upper aveforce 0.0 -1.0 0.0
fix	     6 flow addforce 0.5 0.0 0.0
fix	     7 all enforce2d

# Run
timestep	0.003
thermo		500
thermo_modify	temp mobile

# IO Method: MPI-IO
dump 3 all custom/mpiio 20 dump.*.mpiio x y z   

run		300
```
 
After setting this up, generate the TMIO library (`libtmio.so`) via calling:
```sh
make library
```

Copy the library `libtmio.so`, the LAMMPS executable, the input file `in.flow.pois`, and the sbatch script `sbatch.sh` to the same folder. 
Now, simply call the sbatch command:
```sh
sbatch sbatch.sh
```

Once the simulation is completed, the file `3072.json` should be generated in the current folder.
Note that, if you executed the code with *x* ranks, the tracing file will be named *x*.json. 
To get the dominant frequency with `ftio` simply call:

```sh
ftio 3072.json
```

<p align="right"><a href="#lammps-with-3072-ranks">⬆</a></p>