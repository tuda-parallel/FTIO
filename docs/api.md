# API

The API allows interacting with `ftio` directly, rather than using the command line interface provided in the [`cli`](/ftio/cli/) folder.
Below or several examples of this.

- [API](#api)
	- [General](#general)
	- [Metric Proxy](#metric-proxy)
	- [GekkoFS with Msgpack/JSON support](#gekkofs-with-msgpackjson-support)
	- [GekkoFS with ZMQ](#gekkofs-with-zmq)

## General

The file [`ftio_api.py`](/examples/API/test_api.py) provides an example

<p align="right"><a href="#api">⬆</a></p>

## Metric Proxy

This API allows interaction with the [metric proxy](https://github.com/besnardjb/proxy_v2). Once executed, the proxy outputs a JSON file which can be directly used with this API.
The file [`proxy.py`](/ftio/api/metric_proxy/proxy.py) provides an example. To execute it, simply call:

```sh
python proxy.py
```

The following line in [`proxy.py`](/ftio/api/metric_proxy/proxy.py) can be changed to specify the needed metric and the path to the JSON file:

```py
b, t = parse("some_location/filename.json", "metric")
```

To suppress the output, the function `display_prediction` can be commented out. Moreover, `argv = ["-e", "plotly"]` can be changed to `["-e", "no"]` to disable the plots.

Furthermore, at the end of [`proxy.py`](/ftio/api/metric_proxy/proxy.py), postprocessing occurs to label the phases according to the function label_phases from [`processing.py`](/ftio/post/processing.py).

<p align="right"><a href="#api">⬆</a></p>

## GekkoFS with Msgpack/JSON support

The file [`ftio_gekko.py`](/ftio/api/gekkoFs/ftio_gekko.py) provides an example for the adapted `ftio` api for gekkoFs.
The file [`predictor_gekko.py`](/ftio/api/gekkoFs/predictor_gekko.py) provides an example for `predictor`.

For [`ftio_gekko.py`](/ftio/api/gekkoFs/ftio_gekko.py), the path to the files needs to be specified in the code:

```python
if __name__ == "__main__":
    # absolute path to search all text files inside a specific folder
    # path=r'/d/github/FTIO/examples/API/gekkoFs/JSON/*.json' # For JSON
    path = r"/d/github/FTIO/examples/API/gekkoFs/MSGPACK/write*.msgpack"  # For MSGPCK
    matched_files = glob.glob(path)
    run(matched_files)
```

Similarly, for [`predictor_gekko.py`](/ftio/api/gekkoFs/predictor_gekko.py), the following lines can be adjusted:

```python
def main(args: list[str] = []) -> None:

    n_buffers = 4 # number of buffers 
    args = ["-e", "plotly", "-f", "0.01"] #arguments for ftio
    # path=r'/d/github/FTIO/examples/API/gekkoFs/JSON/*.json' # For JSON
    path = r"/d/github/FTIO/examples/API/gekkoFs/MSGPACK/write*.msgpack"  # For MSGPCK
    matched_files = glob.glob(path)
```

## GekkoFS with ZMQ

The file [`predictor_zmq_gekko`](https://github.com/tuda-parallel/FTIO/blob/main/ftio/api/gekkoFs/predictor_zmq_gekko.py) deploys this functionality. 

Download and compile the file [`test_mpi.cxx`](https://github.com/tuda-parallel/TMIO/blob/main/test/zmq/test_mpi.cxx) from the `TMIO` repo. Then either execute it with a single rank (interactive) or with multiple ranks (with sleep). Simply execute the [Makefile](https://github.com/tuda-parallel/TMIO/blob/main/test/zmq) in the folder:

```sh
make test_mpi

make run_mpi # or run_single_mpi
```

for `ftio`, first navigate to the script and then execute it:

```sh
cd ftio/api/gekkoFs
python3 predictor_zmq_gekko.py 
```

<p align="right"><a href="#api">⬆</a></p>
