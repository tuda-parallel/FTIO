import json
import msgpack
from pathlib import Path
import numpy as np

def parse(file_path, data):
    extension = Path(file_path).suffix
    if "JSON" in extension.upper(): 
        with open(file_path, 'r') as json_file:
                json_data = json.load(json_file)

        for key, value in json_data.items():
            if 'avg_thruput_mib' in key :
                data['avg_thruput_mib'].extend(value)
            elif 'start_t_micro' in key :
                data['start_t_micro'].extend(value)
            elif 'end_t_micro' in key :
                data['end_t_micro'].extend(value)
            elif 'req_size' in key :
                data['req_size'].extend(value)
            elif 'hostname' in key :
                data['hostname'] = value
            elif 'pid' in key :
                data['pid'] = value
            elif 'total_bytes' in key :
                data['total_bytes'] += value
            elif 'total_iops' in key :
                data['total_iops'] += value

    elif "MSG" in extension.upper():
        # Read the binary data
        with open(file_path, "rb") as in_file:
            binary_data = in_file.read()
            
        # Deserialize the MessagePack data 
        unpacker = msgpack.Unpacker()
        unpacker.feed(binary_data)
        data_fields = ["init_t", "hostname", "pid", "start_t_micro", "end_t_micro", "req_size", "total_iops","total_bytes"]
        index = 0
        for item in unpacker:
            if index in [3,4,5]:
                data[data_fields[index]].extend(item)
            else:
                data[data_fields[index]] = item
            index += 1

        b = np.array(data["req_size"])/(np.array(data["end_t_micro"]) - np.array(data["start_t_micro"]))
        data['avg_thruput_mib'].extend(b)
        # calculate the bandwidth
    else:
        raise RuntimeError("Unsupported file format specified")

    return data, extension