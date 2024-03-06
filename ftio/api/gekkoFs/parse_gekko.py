import json


def parse(file_path, data):
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

    return data