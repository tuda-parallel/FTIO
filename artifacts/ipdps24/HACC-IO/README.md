# HACC-IO

Either [extract](#extract-the-provided-trace-file) or [generate](#generate-the-experiment-on-your-system) the trace files as described below. 
Afterward, perform the [offline evaluation](#ftio-offline-evaluation) on the trace file or setup and execute the [online evaluation](#ftio-online-evaluation).

## Extract the provided trace file
Download and extract the file data.zip as described [here](/artifacts/ipdps24/README.md#extracting-the-data-set).
Once extracted, you can find the HACC-IO trace under `data/application_traces/HACC-IO`.

<p align="right"><a href="#hacc-io">⬆</a></p>


## Generate the experiment on your system:
TODO: upload the HACC src files somewhere

<p align="right"><a href="#hacc-io">⬆</a></p>



## FTIO: Offline Evaluation 
If you didn't install `ftio`, first check out version 0.0.1 as described [here](/artifacts/ipdps24/README.md#ftio-version), then install it as described [here](https://github.com/tuda-parallel/FTIO#installation).
The instructions below assume that the trace file is called `3072.jsonl`, which after [extracting](#extract-the-provided-trace-file) the trace file, should be located in `data/application_traces/HACC-IO`.

To get the dominant frequency with `ftio` simply call:
```sh
ftio 3072.jsonl  -v -e no  
```
Remove `-e no` if you want to obtain figures (Fig 12 and 14 from the paper).


<p align="right"><a href="#hacc-io">⬆</a></p>


## FTIO: Online Evaluation
TODO: add 
<p align="right"><a href="#ior">⬆</a></p>