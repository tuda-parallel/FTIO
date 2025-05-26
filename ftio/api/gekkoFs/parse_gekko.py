from pathlib import Path
import json
import msgpack
import numpy as np


def parse(file_path_or_msg, data, io_type="w") -> tuple[dict, str]:
    """Parses data from gekko

    Args:
        file_path_or_msg (_type_): list of files or messages (ZMQ)
        data (_type_): data to append to
        io_type (str, optional): Can be w for write or r for read. Defaults to "w".

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
        data = assign(data, unpacker, io_type)

    # MsgPack
    elif "MSG" in extension.upper():
        # Read the binary data
        with open(file_path_or_msg, "rb") as in_file:
            binary_data = in_file.read()

        # Deserialize the MessagePack data
        unpacker = msgpack.Unpacker()
        unpacker.feed(binary_data)
        data = assign(data, unpacker, io_type)

    # JSON
    elif "JSON" in extension.upper():
        with open(file_path_or_msg, "r") as json_file:
            json_data = json.load(json_file)
        for key, value in json_data.items():
            if "avg_thruput_mib" in key:
                data["avg_thruput_mib"].extend(value)
            elif "start_t_micro" in key:
                data["start_t_micro"].extend(value)
            elif "end_t_micro" in key:
                data["end_t_micro"].extend(value)
            elif "req_size" in key:
                data["req_size"].extend(value)
            elif "hostname" in key:
                data["hostname"] = value
            elif "flush_t" in key:
                data["flush_t"] = value
            elif "pid" in key:
                data["pid"] = value
            elif "total_bytes" in key:
                data["total_bytes"] += value
            elif "total_iops" in key:
                data["total_iops"] += value
            elif "io_type" in key:
                data["io_type"] += value

    else:
        raise RuntimeError("Unsupported file format specified")

    return data, extension


def assign(data: dict, unpacker, io_type="w") -> dict:
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
    skip = False

    for item in unpacker:
        if isinstance(item, dict):
            item = item[data_fields[index]]
        if index in [4, 5, 6]:
            data[data_fields[index]].extend(item)
        elif index == 0:  # find max flush time
            data[data_fields[index]] = max(data[data_fields[index]], item)
        else:
            data[data_fields[index]] = item
            # exit if it is not the right mode
            if index == 3 and item != io_type:
                skip = True
                break
        index += 1

    if not skip:
        # convert later
        b = np.array(object=data["req_size"]) / (
            np.array(data["end_t_micro"]) - np.array(data["start_t_micro"])
        )
        if np.isnan(b).any() or np.isnan(b).any():
            print(
                f'b_rank : {b} \nt_rank_s : {data["start_t_micro"]} \nt_rank_e : {data["end_t_micro"]} \n'
            )
            b[b == np.nan] = 0
            b[b == np.inf] = 0

        data["avg_thruput_mib"].extend(b)
    else:
        # print("Skipping ... ")
        pass

    return data
