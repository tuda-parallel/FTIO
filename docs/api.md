# API

The API allows interacting with `ftio` directly, rather than using the command line interface provided in the [`cli`](/ftio/cli/) folder. Bellow or several examples of this. 

- [API](#api)
	- [General](#general)
	- [Metric Proxy](#metric-proxy)

## General

The file [`ftio_api.py`](/ftio/api/ftio_api.py) provides an example

<p align="right"><a href="#api">⬆</a></p>

## Metric Proxy
This API allows interacting with the [metric proxy](https://github.com/besnardjb/proxy_v2). Once executed, the proxy outputs a JSON file which can be directly used with this API. 
The file [`proxy.py`](/ftio/api/metric_proxy/proxy.py) provides an example. To execute it, simply call:
```sh
python proxy.py
```

The following line in [`proxy.py`](/ftio/api/metric_proxy/proxy.py) can be changed to specify the needed metric and the path to the JSON file:

```py
b, t = parse("some_location/filename.json", "metric")
```

To suppress the output, the function `display_prediction` can be commented out. Moreover, `argv = ["-e", "plotly"]` can be changed to `["-e", "no"]` to disable the plots. 

<p align="right"><a href="#api">⬆</a></p>