import os
import sys
import time
from multiprocessing import Pool, cpu_count
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

from ftio.api.trace_analysis.trace_ftio_v2 import main as trace_ftio
from ftio.api.trace_analysis.trace_analysis import convert_dict, flatten_dict, statistics

# Initialize the console for printing
console = Console()

def process_file(file_path, argv, verbose, name, json=False, index=0, total_files=0):
    try:
        # Call your trace_ftio function (adjust the import and call as necessary)
        res = trace_ftio([file_path] + argv, verbose, json)

        # Create the new file name by replacing the pattern
        base_name = os.path.basename(file_path)
        # if input file is not a json, save ftio result
        if not json:
            json_file = base_name.replace(f"_signal_{name}.csv", f"_freq_{name}.json")
            json_path = os.path.join(os.path.dirname(file_path), json_file)
            # Convert NumPy arrays to lists and save the ftio results
            data_converted = convert_dict(res)
            if json_file.endswith("json"):
                with open(json_path, "w") as file:
                    json.dump(data_converted, file, indent=4)
            else:
                console.print(f"[bold red]Cannot dump Json file in {json_path}[/]")

        flat_res = flatten_dict(res)
        try:
            if json:
                flat_res["job_id"] = base_name.removesuffix('.json')
            else:
                flat_res["job_id"] = base_name.split("_")[0]
            flat_res["file"] = file_path
        except:
            flat_res["job_id"] = "??"
            flat_res["file"] = "??"
            console.print("[bold red]Unable to extract job id[/]")

        # Return the flattened result along with index and total number of files
        return (flat_res, index, total_files)
    except Exception as e:
        console.print(f"\n[bold red]Error processing file {file_path}: {e}[/]")
        return (None, index, total_files)

def main(argv=sys.argv[1:]) -> None:
    verbose = False
    name = "plafrim"
    json = False
    num_procs = -1

    # Specify the name with -n 
    if '-p' in argv:
        index = argv.index('-p')
        num_procs = int(argv[index + 1])
        argv.pop(index)
        argv.pop(index)
    if '-n' in argv:
        index = argv.index('-n')
        name = str(argv[index + 1])
        argv.pop(index)
        argv.pop(index)
    if '-v' in argv:
        index = argv.index('-v')
        argv.pop(index)
        verbose = True
    if '-j' in argv:
        index = argv.index('-j')
        argv.pop(index)
        json = True

    start_time = time.time()
    pattern = f"_signal_{name}.csv"
    df = pd.DataFrame()
    if json:
        pattern = ".json"

    # Handle command-line arguments properly
    if len(argv) > 0:
        folder_path = argv[0]
        argv.pop(0)
    else:
        # folder_path = "/d/traces/traces_from_plafrim/projets/traceflow/sdumont"
        folder_path = "/d/github/FTIO/ftio/api/trace_analysis/plafrim"
        

    folder_path = os.path.abspath(folder_path)
    console.print(f"[bold green]Path is: {folder_path}[/]")

    # Create a list to store all matching csv files
    trace_files = []

    # Walk through all subdirectories and find matching files
    for dirpath, _, filenames in os.walk(folder_path):
        for filename in filenames:
            if filename.endswith(pattern) and "_freq_" not in filename:
                trace_files.append(os.path.join(dirpath, filename))

    if not trace_files:
        console.print(f"[bold red]No files matched the pattern: {pattern}![/]")
        return

    # Create a progress bar
    progress = Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        "[yellow] --  elapsed time",
        TimeElapsedColumn(),
    )

    try:
        with progress:
            task = progress.add_task("[green]Processing files...", total=len(trace_files))

            # Use multiprocessing Pool
            if num_procs == -1:
                num_procs = int(cpu_count()/2)  
            console.print(f"[bold green]Using {num_procs} processes[/]\n")
            # num_procs = min(10, cpu_count())  
            with Pool(processes=num_procs) as pool:
                # Pass the index and total files to process_file
                results = [pool.apply_async(process_file, (file_path, argv, verbose, name, json, i, len(trace_files))) for i, file_path in enumerate(trace_files)]
                
                for result in results:
                    flat_res, index, total_files = result.get()
                    if flat_res:
                        # Process result
                        df = pd.concat([df, pd.DataFrame([flat_res])], ignore_index=True)
                    # Update progress
                    progress.console.print(f"Processed ({index + 1} /{total_files}): {trace_files[index]}")
                    progress.update(task, completed=index + 1)

        progress.console.print("[bold green]All files processed successfully![/]\n")
        console.print(
            f"[blue]FTIO total time:[/] {time.time() - start_time:.4f} seconds\n"
            f"[blue]Location:[/] {folder_path}\n"
            f"[blue]Pattern:[/] {pattern}\n"
        )
        ellapsed_time = f"Execution time {time.time() - start_time:.4f} seconds"
        statistics(df, ellapsed_time)
    except KeyboardInterrupt:
        progress.console.print("[bold red]Keyboard interrupt![/]\n")
        statistics(df)
        sys.exit()
    console.print(f"[blue]Execution time:[/] {time.time() - start_time:.4f} seconds")

if __name__ == "__main__":
    main(sys.argv[1:])
