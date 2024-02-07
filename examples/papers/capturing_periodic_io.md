This file describes how to reproduce the experiments in the Paper entitled:
"Capturing Periodic I/O Using Frequency Techniques" which was published at the IPDPS 2024

The experiments are divided into three parts:
- [Case Studies](#case-studies)
	- [LAMMPS](#lammps)
	- [Nek5000](#nek5000)
	- [Modified HACC-IO](#modified-hacc-io)
- [Limitations of FTIO](#limitations-of-ftio)
- [Use Case: I/O Scheduling](#use-case-io-scheduling)


## Case Studies
For the examples here, `ftio` first needs to be installed (see [Installation](https://github.com/tuda-parallel/FTIO?tab=readme-ov-file#installation)). 

### LAMMPS
Coming soon

### Nek5000
The trace can be downloaded from: <https://hpcioanalysis.zdv.uni-mainz.de/trace/64ed13e0f9a07cf8244e45cc>

after downloading, rename the file to `nek_2048.darshan`. `ftio` can now be called on the complete trace via:

```sh
ftio nek_2048.darshan
```

pass the `-e no` flag to avoid generating plots and just directly obtaining the result from `ftio` on the command line:

```
ftio nek_2048.darshan -e no
```

To limit the time window to 56,000 s, pass the `-te 56000` flag as following:

```
ftio nek_2048.darshan  -te 56000 -e no
```

### Modified HACC-IO
Coming soon




<p align="right"><a href="#top">⬆</a></p>

## Limitations of FTIO

The details for this experiment are provided here: 
<br>
<https://gitlab.inria.fr/hpc_io/ftio_paper_exps_with_synthetic_traces>

<p align="right"><a href="#top">⬆</a></p>

## Use Case: I/O Scheduling
The details for this experiment are provided here:
<br>
<https://gitlab.inria.fr/hpc_io/iosets-ftio-experiments>

<p align="right"><a href="#top">⬆</a></p>



