# Artifacts Reproducibility

This file describes how to reproduce the experiments in the Paper entitled:
"Capturing Periodic I/O Using Frequency Techniques" which was published at the IPDPS 2024

The experiments are divided into three parts:
- [Artifacts Reproducibility](#artifacts-reproducibility)
	- [Case Studies](#case-studies)
		- [LAMMPS](#lammps)
		- [Nek5000](#nek5000)
		- [Modified HACC-IO](#modified-hacc-io)
	- [Limitations of FTIO](#limitations-of-ftio)
	- [Use Case: I/O Scheduling](#use-case-io-scheduling)

FTIO version v0.0.1 was used for all experiments. To checkout to this version, execute:
``` sh
git checkout v0.0.1
```

## Case Studies

`ftio` first needs to be installed (see [Installation](https://github.com/tuda-parallel/FTIO?tab=readme-ov-file#installation)). 

### LAMMPS

This experiment was executed on the Lichtenberg cluster with 3072 ranks. 
Navigate to the LAMMPS folder and follow the instructions provided in the [README.md](/artifacts/capturing_periodic_io_using_frequency_techniques/LAMMPS/README.md). 

<!-- The provided [tar archive](/LAMMPS/lammps.tar.gz) contains not only the result from our -->
<p align="right"><a href="#artifacts-reproducibility">⬆</a></p>


### Nek5000
The trace can be downloaded from: <https://hpcioanalysis.zdv.uni-mainz.de/trace/64ed13e0f9a07cf8244e45cc>.
After downloading, instructions on how to reproduce the results are provided in the [NEK5000/README](/artifacts/capturing_periodic_io_using_frequency_techniques/NEK5000/README.md).


### Modified HACC-IO

Coming soon




<p align="right"><a href="#artifacts-reproducibility">⬆</a></p>

## Limitations of FTIO

The details for this experiment are provided here: 
<br>
<https://gitlab.inria.fr/hpc_io/ftio_paper_exps_with_synthetic_traces>

<p align="right"><a href="#artifacts-reproducibility">⬆</a></p>


## Use Case: I/O Scheduling
The details for this experiment are provided here:
<br>
<https://gitlab.inria.fr/hpc_io/iosets-ftio-experiments>

<p align="right"><a href="#artifacts-reproducibility">⬆</a></p>




