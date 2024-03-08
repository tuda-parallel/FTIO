
### ZMQ with generic format
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


### ZMQ and TMIO
`ftio` and `predictor` can be used with [`TMIO`](https://github.com/tuda-parallel/TMIO/). This is still under development. 
For communication, a port is used. From the sender side ([`TMIO`](https://github.com/tuda-parallel/TMIO/)), the port can be specified in a local file called `ftio_port`. The file contains just a single line, for example:
```sh
tcp://127.0.0.1:XXXX
```
From the receiver side (`ftio`), the port can be specified by `--zmq_source` flag.

#### Setup
First, compile TMIO with ZMQ. Go to the build folder in [`TMIO`](https://github.com/tuda-parallel/TMIO/) and execute:
```sh
make zmq
```
Afterwards, just execute the program

```sh
mpirun -np 8    ./test_run 
```

For `ftio`, simply launch the script with:

```sh
ftio --zmq --zmq_source tmio -m write_async -f 100
```

For `predictor`, execute:

```sh
predictor --zmq --zmq_source tmio -m write_async -f 100
```


```
<p align="right"><a href="#file-formats-and-tools">⬆</a></p>
