import os 
import re
# import shutil
import time
import numpy as np
from ftio.freq.helper import MyConsole

CONSOLE = MyConsole()
CONSOLE.set(True)

def setup_cargo(tmp_args):
    if tmp_args.cargo:
        #1. Perform stage in outside FTIO with cpp
        #2. Setup für Cargo Stage-out für cargo_ftio
        call = f"{tmp_args.cargo_bin}/cargo_ftio --server {tmp_args.cargo_server} --run"
        CONSOLE.print("\n[bold green][Init][/][green]" + call +"\n")
        os.system(call)

        # 3. tells cargo that for all next cargo_ftio calls use the cpp
        # input is relative from GekokFS
        call = f"{tmp_args.cargo_bin}/ccp --server {tmp_args.cargo_server} --input / --output {tmp_args.stage_out_path} --if gekkofs --of parallel"
        CONSOLE.print("\n[bold green][Init][/][green]" + call + "\n")
        os.system(call)
        # 4. trigger with the thread
        # 5. Do a stage out outside FTIO with cargo_ftio --run


def trigger_cargo(sync_trigger,args):
    """sends cargo calls. For that in extracts the predictions from `sync_trigger` and examines it. 

    Args:
        sync_trigger (_type_): _description_
    """
    not_in_time = 0
    while True:
        try:
            if not sync_trigger.empty():
                skip_flag = False 
                prediction = sync_trigger.get()
                t = time.time() - prediction['t_wait']  # time waiting so far
                # CONSOLE.print(f"[bold green][Trigger] queue wait time = {t:.3f} s[/]\n")
                if not np.isnan(prediction['freq']):
                    #? 1) Find estimated number of phases and skip in case less than 1
                    # n_phases = (prediction['t_end']- prediction['t_start'])*prediction['freq']
                    # if n_phases <= 1:
                    #     CONSOLE.print(f"[bold green][Trigger] Skipping this prediction[/]\n")
                    #     continue
                    
                    #? 2) Time analysis to find the right instance when to send the data
                    target_time = prediction['t_end'] + 1/prediction['freq']
                    gkfs_elapsed_time = prediction['t_flush'] + t  # t  is the waiting time in this function. t_flush contains the overhead of ftio + when the data was flushed from gekko
                    remaining_time = (target_time - gkfs_elapsed_time ) 
                    CONSOLE.print(f"[bold green][Trigger {prediction['source']}][/][green] Target time = {target_time:.3f} -- Gekko time = {gkfs_elapsed_time:.3f} -> sending cmd in {remaining_time:.3f} s[/]\n")
                    if remaining_time > 0:
                        countdown = time.time() + remaining_time
                        # wait till the time elapses:
                        while time.time() < countdown:
                            pass
                            #? 3) Skip in case new prediction is available  
                            # if not sync_trigger.empty():
                            #     skip_flag = True

                        if not skip_flag:
                            stage_files(args,prediction)
                        else:
                            # TODO: skipp only oif the predictions overlap 
                            CONSOLE.print("[bold green][Trigger][/][yellow] Skipping, new prediction is ready[/]\n")

                    else:
                        not_in_time += 1
                        if not_in_time == 3:
                            CONSOLE.print("[bold green][Trigger][/][yellow] Not in time 3 times, triggering flush[/]\n")
                            stage_files(args,prediction)
                            not_in_time = 0
                        else:
                            CONSOLE.print("[bold green][Trigger][/][yellow] Skipping, not in time[/]\n")

            time.sleep(0.01)
        except KeyboardInterrupt:
            exit()



def stage_files(args, prediction):
    """stages the files 

    Args:
        args (argParse): Parsed command line arguments
        prediction (dict): Result from FTIO
    """
    period = 1/prediction['freq'] if prediction['freq'] > 0 else 0
    text = f"frequency: {prediction['freq']}\nperiod: {period} \nconfidence: {prediction['conf']}\nprobability: {prediction['probability']}\n"
    CONSOLE.print(f"[bold green][Trigger][/][green] {text}\n")
    if args.cargo:
        move_files_cargo(args)
    else: #standard move
        # TODO: needs gkfs flags to move files
        move_files_os(args.stage_in_path,args.stage_out_path,args.regex)



def move_files_cargo(args):
    # call = f"{args.cargo_bin}/cargo_ftio --server {args.cargo_server} -c {prediction['conf']} -p {prediction['probability']} -t {1/prediction['freq']}"
    call = f"{args.cargo_bin}/cargo_ftio --server {args.cargo_server} --run"
    CONSOLE.print(f"[bold green][Trigger][/][green] {call}")
    os.system(call)


def move_files_os(src_dir, dest_dir, relevant_pattern=None):
    """
    Move all files and directories from src_dir to dest_dir, ignoring items matching the regex pattern.

    Args:
        src_dir (str): Path to the source directory.
        dest_dir (str): Path to the destination directory.
        ignore_pattern (str): Regex pattern to ignore files/directories (optional).
    """
    CONSOLE.print("[bold green][Trigger][/][green] Moving files\n")
    # Ensure both source and destination directories exist
    if not os.path.exists(src_dir):
        print(f"Source directory '{src_dir}' does not exist.")
        return
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    regex = None
    # Compile the regex pattern if provided
    if relevant_pattern:
        CONSOLE.print(f"[bold green][Trigger][/][green] Using pattern: {relevant_pattern}[/]\n")
        regex = re.compile(relevant_pattern)

    # Iterate over all items in the source directory
    for root, _, files in os.walk(src_dir):  # Use os.walk for traversing directories
        # Determine the relative path from the source directory
        relative_path = os.path.relpath(root, src_dir)
        target_dir = os.path.join(dest_dir, relative_path)

        # Ensure the target directory exists
        os.makedirs(target_dir, exist_ok=True)

        for file_name in files:
            # Check if the file matches the ignore pattern
            if regex and regex.match(file_name):
                src_file = os.path.join(root, file_name)
                dest_file = os.path.join(target_dir, file_name)
                try:
                    # Move file or directory using geko flags
                    # shutil.move(src_file, dest_file)
                    CONSOLE.print("[bold green][Trigger][/][yellow] -- Moving files is currently only simulated --[/]\n")
                    print(f"Moved: {src_file} -> {dest_file}")
                except Exception as e:
                    print(f"Error moving '{src_file}': {e}")
            else:
                print(f"Ignored: {file_name}")
