import os
import sys
import time
from multiprocessing import Pool, cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TimeRemainingColumn,TaskProgressColumn, TextColumn, BarColumn

from ftio.api.trace_analysis.trace_ftio_v2 import main as trace_ftio
from ftio.api.trace_analysis.trace_analysis import convert_dict, flatten_dict, statistics

# Initialize the console for printing
console = Console()

def process_file(file_path, argv, verbose, name, json=False, index=0):
    error = ''
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
    except Exception as e:
        console.print(f"\n[bold red]Error processing file {file_path}: {e}[/]")
        error = str(e)
        flat_res = None

    return flat_res, index, file_path, error


def main(argv=sys.argv[1:]) -> None:
    verbose = False
    name = "plafrim"
    json = False
    num_procs = -1
    res_path = "."

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
    if '-o' in argv:
        index = argv.index('-o')
        res_path = str(argv[index + 1])
        argv.pop(index)
        argv.pop(index)

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

    total_files = len(trace_files)
    # Create a progress bar
    progress = Progress(
        SpinnerColumn(),
        # *Progress.get_default_columns(),
        TextColumn("[progress.description]{task.description} ({task.completed}/{task.total})"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        "[yellow]-- runtime",
        TimeElapsedColumn(),
    )

    try:
        with progress:
            # Use multiprocessing Pool
            if num_procs == -1:
                num_procs = int(cpu_count()/2)  
            
            console.print(f"[bold green]Using {num_procs} processes[/]\n")
            task = progress.add_task("[green]Processing files", total=total_files)
            
            # List to store failed file details
            failed_files = []
            
            # use future or apply_async 
            future = True #managing tasks without blocking others due to slow processes
            
            if future:
                counter = 0
                with ProcessPoolExecutor(max_workers=num_procs) as executor:
                    # Submit tasks to the executor
                    futures = {executor.submit(process_file, file_path, argv, verbose, name, json, i): i for i, file_path in enumerate(trace_files)}
                    
                    # Process results as they complete
                    for future in as_completed(futures):
                        # index = futures[future]
                        flat_res, index, file_path, error = future.result()
                        if flat_res: # Process result
                            df = pd.concat([df, pd.DataFrame([flat_res])], ignore_index=True)
                        if error:  # Log any failed files
                            failed_files.append((file_path, error))
                        # Update progress
                        progress.console.print(f"Processed ({index + 1}/{len(trace_files)}): {trace_files[index]}")
                        counter += 1
                        progress.update(task, completed=counter)
            else:
                with Pool(processes=num_procs) as pool:
                    # Pass the index and total files to process_file
                    results = [pool.apply_async(process_file, (file_path, argv, verbose, name, json, index)) for i, file_path in enumerate(trace_files)]
                    
                    for result in results:
                        flat_res, index, file_path, error = result.get()
                        if flat_res: # Process result
                            df = pd.concat([df, pd.DataFrame([flat_res])], ignore_index=True)
                        if error:  # Log any failed files
                            failed_files.append((file_path, error))
                        # Update progress
                        progress.console.print(f"Processed ({index + 1}/{total_files}): {trace_files[index]}")
                        progress.update(task, completed=index + 1)
        
    
        # After processing, log the files that failed
        if failed_files:
            progress.console.print(
                f"\n[bold green]{total_files} files processed successfully![/]\n"
                f"[bold red]{len(failed_files)} files failed[/]\n"
            )
            console.print("\n[bold yellow]The following files failed to process:[/]")
            with open(f"{res_path}/log.err", 'w') as log:
                for file_path, error in failed_files:
                    console.print(f"[bold red]{file_path}[/]")
                    log.write(f"{file_path}: {error}\n")
        else:
            progress.console.print("\n[bold green]All files processed successfully![/]\n")

        console.print(
            f"[blue]FTIO total time:[/] {time.time() - start_time:.4f} seconds\n"
            f"[blue]Location:[/] {folder_path}\n"
            f"[blue]Pattern:[/] {pattern}\n"
        )
        ellapsed_time = f"Execution time {time.time() - start_time:.4f} seconds"
        statistics(df, ellapsed_time,res_path)
    except KeyboardInterrupt:
        progress.console.print("[bold red]Keyboard interrupt![/]\n")
        statistics(df, "",res_path)
        sys.exit()
    console.print(f"[blue]Execution time:[/] {time.time() - start_time:.4f} seconds")

if __name__ == "__main__":
    main(sys.argv[1:])
