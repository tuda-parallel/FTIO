import argparse
import os

def process_log_files(input_files, output_file):
    last_timestamp = 0
    with open(output_file, 'w') as outfile:
        for input_file in input_files:
            with open(input_file, 'r') as infile:
                for line in infile:
                    # Split line by spaces and extract the relevant columns
                    columns = line.split()
                    
                    # Extract the timestamp (2nd column) and offset it
                    timestamp = float(columns[2])
                    
                    timestamp += last_timestamp
                    
                    # Update the timestamp in the line
                    columns[2] = f"{timestamp:.6f}"
                    
                    # Join the columns back into a string and write to the output file
                    outfile.write(" ".join(columns) + '\n')
                    
            # Update the last timestamp to the current line's timestamp
            last_timestamp = timestamp

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Process log files and offset timestamps.")
    
    # Add arguments for input files and output file
    parser.add_argument('input_files', nargs='+', help="List of input log files to process")
    parser.add_argument('output_file', help="Output file to store the processed logs")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Process the log files
    process_log_files(args.input_files, args.output_file)
    print(f"Processed log files and saved the result to {args.output_file}")

if __name__ == "__main__":
    main()
