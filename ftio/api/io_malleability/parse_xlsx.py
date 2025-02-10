import os
import pandas as pd
import json
import argparse


def parse_args():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Convert an XLSX file to JSON.")
    # Set default values for the file
    parser.add_argument("--file", type=str, default="IOTraces.xlsx", help="Path to the Excel file (default: IOTraces.xlsx)")

    return parser.parse_args()


def main(args=parse_args()):
    # Resolve the file path
    file_path = os.path.join(os.path.dirname(__file__), args.file)

    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Error: File '{file_path}' not found.")

    # Read the Excel file
    df = pd.read_excel(file_path)

    # Ensure column names are correctly read (trim any whitespace)
    df.columns = df.columns.str.strip()

    # Initialize variables
    ranks = 0
    total_bytes = 0
    b = []
    t = []
    names = df.columns.to_list()

    # Extract relevant data
    for name in names:
        name_lower = name.lower()
        if "i/o bandwidth" in name_lower:
            b.extend(df[name].tolist())
        elif "time stamp" in name_lower:
            t.extend(df[name].tolist())
        elif "rank" in name_lower:
            ranks = df[name].tolist()[0]
        elif "total bytes" in name_lower:
            total_bytes = df[name].tolist()[0]

    # Construct JSON format
    json_data = {
        "write_sync": {
            "total_bytes": total_bytes,
            "number_of_ranks": ranks,
            "bandwidth": {
                "b_overlap_avr": b,
                "t_overlap": t
            }
        }
    }

    # Save JSON to file
    output_file = "output.json"
    with open(output_file, "w") as json_file:
        json.dump(json_data, json_file, indent=4)

    # Print JSON for verification
    print(json.dumps(json_data, indent=4))



# Ensure script runs only when executed directly
if __name__ == "__main__":
    main()
