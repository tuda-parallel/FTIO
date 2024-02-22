# HACC-IO

Either [generate](#execute-the-experiment-on-your-system) or [extract](#extract-the-provided-trace-file) the provided trace file.
Afterward, perform the [offline evaluation](#ftio-offline-evaluation) on the trace file or setup and execute the [online evaluation]()


## Execute the experiment on your system:
TODO: upload the HACC src files somewhere

<p align="right"><a href="#hacc-io">⬆</a></p>


## Extract the provided trace file
Download and extract the file data.zip as described [here](/artifacts/ipdps24/README.md#extracting-the-data-set).
Once extracted, you can find the HACC-IO trace under `application_traces/HACC-IO`.

<p align="right"><a href="#hacc-io">⬆</a></p>


## FTIO: Offline Evaluation 
[Install FTIO](https://github.com/tuda-parallel/FTIO#installation).
The instructions below assume that the trace file is called `3072.jsonl`.

To get the dominant frequency with `ftio` simply call:
```sh
ftio 3072.jsonl  -v -e no  
```
Remove `-e no` if you want to obtain figures (Fig 12 and 14 from the paper).


<p align="right"><a href="#hacc-io">⬆</a></p>


## FTIO: Online Evaluation

<p align="right"><a href="#ior">⬆</a></p>