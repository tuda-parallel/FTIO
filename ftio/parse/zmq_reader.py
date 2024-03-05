import time
import msgpack
from ftio.parse.input_template import init_data
from rich.console import Console


def extract(msg, args:list) -> tuple[dict, int]:
    # init
    start = time.time()
    ranks = 0
    mode, io_data, io_time = init_data(args)

    unpacked_data = msgpack.unpackb(msg)

    # Access the data
    ranks           = unpacked_data["ranks"]
    b               = unpacked_data["b"]
    ts              = unpacked_data["ts"]
    te              = unpacked_data["te"]
    # received_float  = unpacked_data["floatData"]


    io_data["bandwidth"]["b_rank_avr"] = b
    io_data["bandwidth"]["t_rank_s"]   = ts
    io_data["bandwidth"]["t_rank_e"]   = te

    console = Console()
    console.print(f"[cyan]Elapsed time:[/] {time.time()-start:.3f} s")
    # io_time[f"delta_t_{kind}"] = 0
    
    #pack everything
    data = {
        f"{mode}": io_data,
        "io_time": io_time,
    }

    return data, ranks









#% C++ code
#%--------------------
# #include <iostream>
# #include <zmq.hpp>
# #include <msgpack.hpp>

# int main() {
#     zmq::context_t context(1);
#     zmq::socket_t socket(context, ZMQ_PUSH);

#     socket.bind("tcp://127.0.0.1:5555");

#     // Create a MessagePack object to hold the data
#     msgpack::sbuffer buffer;
#     msgpack::packer<msgpack::sbuffer> packer(&buffer);

#     // Pack the data into the MessagePack buffer
#     packer.pack_map(3);
#     packer.pack("intData");
#     packer.pack(42);
#     packer.pack("floatData");
#     packer.pack(3.14);

#     // Pack the arrayData
#     packer.pack("arrayData");
#     packer.pack_array(5);
#     packer.pack(1.0);
#     packer.pack(2.0);
#     packer.pack(3.0);
#     packer.pack(4.0);
#     packer.pack(5.0);

#     zmq::message_t message(buffer.size());
#     memcpy(message.data(), buffer.data(), buffer.size());

#     socket.send(message, zmq::send_flags::none);

#     return 0;
# }
