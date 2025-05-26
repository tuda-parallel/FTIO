import time
import msgpack
from rich.console import Console
from ftio.parse.input_template import init_data


def extract(msgs, args: list) -> tuple[dict, int]:
    # init
    start = time.time()
    mode, io_data, io_time = init_data(args)

    # unpack data
    unpacked_data = msgpack.unpackb(msgs)

    # Access the data
    if "ranks" in unpacked_data:
        ranks = unpacked_data["ranks"]
    else:
        ranks = 0
    b = unpacked_data["b"]
    ts = unpacked_data["ts"]
    te = unpacked_data["te"]
    # received_float  = unpacked_data["floatData"]

    io_data["bandwidth"]["b_rank_avr"] = b
    io_data["bandwidth"]["t_rank_s"] = ts
    io_data["bandwidth"]["t_rank_e"] = te

    console = Console()
    console.print(f"[cyan]Elapsed time:[/] {time.time()-start:.3f} s")
    # io_time[f"delta_t_{kind}"] = 0

    # pack everything
    data = {
        f"{mode}": io_data,
        "io_time": io_time,
    }

    return data, ranks
