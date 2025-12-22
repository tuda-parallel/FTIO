import json
from pathlib import Path

import msgpack
import numpy as np


def parse(file_path_or_msg, data, io_type="w", debug_level: int = 0) -> tuple[dict, str]:
    """Parses data from gekko

    Args:
        file_path_or_msg (list): list of files or messages (ZMQ)
        data (dict): data to append to
        io_type (str, optional): Can be w for write or r for read. Defaults to "w".
        debug_level (int, optional): Debug flag for printing fields. Defaults to False.

    Raises:
        RuntimeError: _description_

    Returns:
        tuple[dict, str]: _description_
    """
    if isinstance(file_path_or_msg, bytes):
        extension = "ZMQ"
    else:
        extension = Path(file_path_or_msg).suffix

    # ZMQ
    if "ZMQ" in extension.upper():
        # if data is no struct:
        # unpacked_data = msgpack.unpackb(file_path_or_msg)
        # else:
        unpacker = msgpack.Unpacker()
        unpacker.feed(file_path_or_msg)
        data = assign(data, unpacker, io_type, debug_level)

    # MsgPack
    elif "MSG" in extension.upper():
        # Read the binary data
        with open(file_path_or_msg, "rb") as in_file:
            binary_data = in_file.read()

        # Deserialize the MessagePack data
        unpacker = msgpack.Unpacker()
        unpacker.feed(binary_data)
        data = assign(data, unpacker, io_type, debug_level)

    # JSON
    elif "JSON" in extension.upper():
        with open(file_path_or_msg, "r") as json_file:
            json_data = json.load(json_file)
        for key, value in json_data.items():
            if "avg_throughput" in key:
                data["avg_throughput"].extend(value)
            elif "start_t_micro" in key:
                data["start_t_micro"].extend(value)
            elif "end_t_micro" in key:
                data["end_t_micro"].extend(value)
            elif "req_size" in key:
                data["req_size"].extend(value)
            elif "hostname" in key:
                data["hostname"] = value
            elif "flush_t_micro" in key:
                data["flush_t_micro"] = value
            elif "pid" in key:
                data["pid"] = value
            elif "total_bytes" in key:
                data["total_bytes"] += value
            elif "total_iops" in key:
                data["total_iops"] += value
            elif "io_type" in key:
                data["io_type"] += value

        scale = [1.07 * 1e6, 1e-3, 1e-3]
        if len(data["avg_throughput"]) > 0:
            data["avg_throughput"] = np.array(data["avg_throughput"]) * scale[0]
            data["t_start"] = np.array(data["start_t_micro"]) * scale[1]
            data["t_end"] = np.array(data["end_t_micro"]) * scale[2]
            if "flush_t" in data:
                data["t_flush"] = data["flush_t_micro"] * scale[2]

    else:
        raise RuntimeError("Unsupported file format specified")

    return data, extension


def assign(data: dict, unpacker, io_type="w", debug_level: int = 0) -> dict:
    data_fields = [
        "flush_t",
        "hostname",
        "pid",
        "io_type",
        "start_t_micro",
        "end_t_micro",
        "req_size",
        "total_iops",
        "total_bytes",
    ]
    index = 0
    t_flush = 0
    skip = False
    for item in unpacker:
        if isinstance(item, dict):
            item = item[data_fields[index]]

        if index == 0:  # find max flush time
            t_flush = max(data["t_flush"], item * 1e-6)
        elif index == 3:
            if item != io_type:
                skip = True
                break
            else:
                data["t_flush"] = t_flush
        elif index == 4:
            data["t_start"].extend([v * 1e-6 for v in item])
        elif index == 5:
            data["t_end"].extend([v * 1e-6 for v in item])
        elif index == 6:
            data["req_size"].extend(item)
        else:
            data[data_fields[index]] = item
            # exit if it is not the right mode
        index += 1

    # convert from µs to s
    if not skip:
        duration = np.array(data["t_end"]) - np.array(data["t_start"])
        duration[duration == 0] = 1e-6
        b = np.array(data["req_size"]) / duration  # in B/s

        if np.isnan(b).any():
            print(
                f'b_rank : {b} \nt_rank_s : {data["t_start"]} \nt_rank_e : {data["t_end"]} \n'
            )
            b[np.isnan(b)] = 0
            b[np.isinf(b)] = 0

        data["avg_throughput"].extend(b)
        if debug_level > 0:
            total_req = np.sum(data["req_size"])
            print(f"Total request size: {total_req} bytes ({total_req/1e9:.3f} GB)")
            if debug_level > 1:
                # averaged throughput
                print(
                    f"Transfer speed: {np.sum(np.array(data["req_size"]))/(max(np.array(data["t_end"])) - min(np.array(data["t_start"]))) *1e-9} GB/s"
                )
                print(f"Start time: {np.array(data['t_start'])} sec")
                print(f"End time: {np.array(data['t_end'])} sec")
                print(f"Request size: {np.array(data['req_size'])} bytes")
                # Actual Throughput
                print(f"Bandwidth: {b} b/s")
                if debug_level > 2:
                    print(f"Total bytes: {data['total_bytes']} bytes")
                    print(f"Total IOPS: {data['total_iops']} bytes")

    return data
