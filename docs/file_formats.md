# File Formats and Tools

Supported File Formats are:
- [File Formats and Tools](#file-formats-and-tools)
	- [JSON](#json)
	- [JSONL](#jsonl)
	- [MessagePack](#messagepack)
	- [Darshan](#darshan)
	- [Recorder](#recorder)
	- [Custom File Format](#custom-file-format)
	- [ZMQ](#zmq)

## JSON
TBD

<p align="right"><a href="#file-formats-and-tools">⬆</a></p>

## JSONL
TBD

<p align="right"><a href="#file-formats-and-tools">⬆</a></p>

## MessagePack
TBD

<p align="right"><a href="#file-formats-and-tools">⬆</a></p>

## Darshan
standard Darshan file. By default, `ftio` first tries to read the DXT trace. 
In case it contains a DXT trace, specify with  
`-x DXT_MODE` the data to extract from the Darshan trace (`DXT_POSIX` or `DXT_MPIIO` (default)).
If the file does not contain a DXT trace, `ftio` tires to read the heat map. In both cases, pydarshan to read the file.

As the collected values a re per rank level, `ftio` internally overlaps them to obtain the application-level bandwidth.

<p align="right"><a href="#file-formats-and-tools">⬆</a></p>

## Recorder
TBD

<p align="right"><a href="#file-formats-and-tools">⬆</a></p>


## Custom File Format
`ftio` supports custom file formats specified with regex. These values can be scaled in case they are not in SI units. 
The file must currently have the `txt`extension. 
For that, `ftio` provides two dictionaries that must be provided (pattern and translate) in a custom file similar as in the [convert](/ftio/parse/custom_patterns.py) function. 

1. _**pattern** (dict[str, str])_: dictionary containing the name and a regex expression to find the custom pattern.
2. _**translate** (dict[str, tuple[str, (optional)float]])_: dictionary containing matching filed from [sample.py](/ftio/parse/sample.py) and the matching name from the pattern. The unit can be optionally specified

An example is provided in [example/txt](/examples/txt/). Navigate to this folder. There, a file called [`custom_input.py`](/examples/txt/custom_input.py) is located and contains the following: 

```python
pattern = {
	"avg_thruput_mib": r"avg_thruput_mib:\s+\[([\d.\d,\s]+)\]",
	"end_t_micro": r"end_t_micro:\s+\[([\d,\s]+)\]",
	"start_t_micro": r"start_t_micro:\s+\[([\d,\s]+)\]",
	"total_bytes": r"total_bytes:\s+(\d+)",
	"total_iops": r"total_iops:\s+(\d+)",
	}

# Define map according to sample.py class, along with the scale if any:
# ftio_field: ("custom_name", scale)
# ftio unit are default in bytes, b/s, ...
# scale applies ftio_field = custom_name*scale
translate = {
	"bandwidth": {
		"b_rank_avr": ("avg_thruput_mib",1.07*1e+6),
		"t_rank_e": ("end_t_micro", 1e-3),
		"t_rank_s": ("start_t_micro", 1e-3)
		},
	"total_bytes": "total_bytes",
	"max_io_ops_per_rank": "total_iops"
	}
```

The fields in translate must match the fields in [sample.py](/ftio/parse/sample.py). The field bandwidth as its three fields (`b_rank_avr`, `t_rank_e`, and `t_rank_s`) are mandatory. Though these fields are indexed with `_rank_`, they can be on any level higher than rank. Note that in case the application-level bandwidth is provided, `t_rank_e` is not needed. 
Other supported fields include (from [sample.py](/ftio/parse/sample.py)):
```python
# cutout from /ftio/parse/sample.py
⋮
def __init__(self, values, io_type, args):
        self.type # 'read_sync', 'read_async_t', 'write_async_t','write_sync'                        
        self.max_bytes_per_rank # maximum bytes transferred per rank per phase
        self.max_bytes_phase # maximum bytes transferred per rank during all phases
        self.total_bytes # total transferred bytes
        self.max_io_phases_per_rank      # maximum I/O phases
        self.total_io_phases             # total I/O phases
        self.max_io_ops_per_rank         # maximum I/O operations per rank
        self.max_io_ops_in_phase         # maximum I/O operation per phase
        self.total_io_ops                # Total I/O operations
        self.number_of_ranks             # number of ranks that did I/O
        self.bandwidth                   # Dictionary containing the fileds b_rank_avr, t_rank_e, and t_rank_s

⋮
```

Next, the fields indicated by [`custom_input.py`](/examples/txt/custom_input.py) match the fields in the file [`2.txt`](/examples/txt/2.txt), which contains, for example:

```
avg_thruput_mib: [0.0,0.0,1000.0,1000.0,0.0,0.0,1000.0,1000.0,0.0,0.0,1000.0,1000.0,0.0,0.0]
start_t_micro: [0500,0000,10500,10000,20500,20000,30500,30000,40500,40000,50500,50000,60500,60000]
end_t_micro: [5000,4500,15000,14500,25000,24500,35000,34500,45000,44500,55000,54500,65000,64500]
hostname: "XXX"
pid: 2063022
total_bytes: 15000
total_iops: 1024
```

Finally, `ftio` can be executed with the `-cf` flag pointing to the location of `custom_input.py`.
For this example, all files are in the current working directory [example/txt](/examples/txt/).
Thus, `ftio` can be simply executed by:
```sh
ftio 2.txt -cf custom_input.py
```
<p align="right"><a href="#file-formats-and-tools">⬆</a></p>




## ZMQ
`ftio` supports ZMQ. This is still under development.

```sh
predictor --zmq
```

The following C++ file can be used for communication:
```c++
#include <iostream>
#include <zmq.hpp>
#include <msgpack.hpp>

int main() {
    zmq::context_t context(1);
    zmq::socket_t socket(context, ZMQ_PUSH);

    socket.bind("tcp://127.0.0.1:5555");

    // Create a MessagePack object to hold the data
    msgpack::sbuffer buffer;
    msgpack::packer<msgpack::sbuffer> packer(&buffer);

    // Pack the data into the MessagePack buffer
    packer.pack_map(4);
    packer.pack("ranks");
    packer.pack(8);
    // packer.pack("floatData");
    // packer.pack(3.14);

    // Pack the arrays
    packer.pack("b");
    packer.pack_array(5);
    packer.pack(3.0);
    packer.pack(0.0);
    packer.pack(3.0);
    packer.pack(0.0);
    packer.pack(3.0);

	packer.pack("ts");
    packer.pack_array(5);
    packer.pack(1.0);
    packer.pack(2.0);
    packer.pack(3.0);
    packer.pack(4.0);
    packer.pack(5.0);

	packer.pack("te");
    packer.pack_array(5);
    packer.pack(5.0);
    packer.pack(6.0);
    packer.pack(7.0);
    packer.pack(8.0);
    packer.pack(9.0);
    zmq::message_t message(buffer.size());
    memcpy(message.data(), buffer.data(), buffer.size());
    socket.send(message, zmq::send_flags::none);

    return 0;
}

```
<p align="right"><a href="#file-formats-and-tools">⬆</a></p>
