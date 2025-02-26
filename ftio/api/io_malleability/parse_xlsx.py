import os
import pandas as pd
import json
import argparse
from rich.console import Console
import numpy as np

from ftio.parse.bandwidth import overlap

def parse_args():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Convert an XLSX file to JSON.')
    # Set default values for the file
    parser.add_argument('--file', '-f', type=str, default='IOTraces_2.xlsx', help='Path to the Excel file (default: IOTraces.xlsx)')
    parser.add_argument('--out', '-o',type=str, default='output.json', help='Output file name')
    parser.add_argument('-i', '--interactive', dest='interactive', action = 'store_true', help='If passed, allows to select the relevant field for the bandwith')
    parser.add_argument('-b', '--bandwidth_column', default=-1, dest='b', type = int, help ='specifies the column directly for bandwidth (see -i for help)')
    parser.add_argument('-t', '--time_column', default=-1, dest='t', type = int, help ='specifies the column directly for time (see -i for help)')
    
    

    return parser.parse_args()


def main(args=parse_args()):
    console = Console()

    # Resolve the file path
    file_path = os.path.join(os.path.dirname(__file__), args.file)

    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'Error: File "{file_path}" not found.')

    # Read the Excel file
    df = pd.read_excel(file_path)

    # Ensure column names are correctly read (trim any whitespace)
    df.columns = df.columns.str.strip()

    # Initialize variables
    ranks = 0
    total_bytes = 0
    b = []
    t_s = []
    io_time = []
    names = df.columns.to_list()

    # Extract relevant data
    for name in names:
        if isinstance(name,str):
            name_lower = name.lower()
            if 'i/o bandwidth' in name_lower:
                b.extend(df[name].tolist())
            elif 'time stamp' in name_lower:
                t_s.extend(df[name].tolist())
            elif 'i/o time' in name_lower:
                io_time.extend(df[name].tolist())
            elif 'rank' in name_lower:
                ranks = int(df[name].tolist()[0])
            elif 'total bytes' in name_lower:
                total_bytes = int(df[name].tolist()[0])

    # for i,value in enumerate(t):
        

    if args.interactive:
        for i, value in enumerate(names):
            console.print(f'[{i}]: {value}')
        b = []
        t_s = []
        value = input('\nPlease select the column to map to bandwidth:\n> ')
        value = int(value)
        console.print(f'[green]> bandwidth set to [{value}]: {names[value]}[/]')
        b.extend(df[names[value]].tolist())
        value = input('\nPlease select the column to map to time:\n> ')
        value = int(value)
        console.print(f'[green]> time set to [{value}]: {names[value]}[/]')
        t_s.extend(df[names[value]].tolist())
        value = input('\nPlease select the column to map to I/O time:\n> ')
        value = int(value)
        console.print(f'[green]> time set to [{value}]: {names[value]}[/]')
        io_time.extend(df[names[value]].tolist())

        
    if args.b >= 0:
        b = []
        value = int(args.b)
        console.print(f'[green]> Selected [{value}]: {names[value]}[/]')
        b.extend(df[names[value]].tolist())

    if args.t >= 0:
        t_s = []
        value = int(args.t)
        console.print(f'[green]> Selected [{value}]: {names[value]}[/]')
        t_s.extend(df[names[value]].tolist())


    # Remove matching NaNs
    valid_indices = [i for i in range(len(b)) if not pd.isna(b[i]) and not pd.isna(t_s[i])]
    # Filter b and t using the valid indices
    b = [b[i] for i in valid_indices]
    t_s = [t_s[i] for i in valid_indices]
    if io_time:
        console.print('[green]> Calculating overlap metrics[/]')
        io_time = [io_time[i] for i in valid_indices]
        t_e = np.array(t_s) + np.array(io_time)
        b, t = overlap(b,t_s, t_e)
    else:
        t = t_s

    # Construct JSON format
    json_data = {
        'write_sync': {
            'total_bytes': total_bytes,
            'number_of_ranks': ranks,
            'bandwidth': {
                'b_overlap_avr': b,
                't_overlap': t
            }
        }
    }

    # Save JSON to file
    with open(args.out, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)

    # Print JSON for verification
    # print(json.dumps(json_data, indent=4))
    console.print(f'[green]--- done ---[/]')
    



# Ensure script runs only when executed directly
if __name__ == '__main__':
    main()
