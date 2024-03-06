import sys
from multiprocessing import Manager
from rich.console import Console
import glob
import ftio.prediction.monitor as pm
from ftio.prediction.helper import print_data, export_extrap
from ftio.prediction.async_process import handle_in_process
from ftio.prediction.probability import probability
from ftio.prediction.helper import get_dominant, get_hits
from ftio.api.gekkoFs.ftio_gekko import run
from ftio.prediction.analysis import display_result, save_data, data_analysis

def main(args: list[str] = []) -> None:

    n_buffers = 4
    args =["-e", "plotly", "-f", "0.01"]
    path=r'/d/github/FTIO/examples/gekkoFs/JSON/*.json'
    matched_files = glob.glob(path)

    # Init
    manager = Manager()
    queue = manager.Queue()
    data = manager.list() # stores prediction
    aggregated_bytes = manager.Value("d", 0.0)
    hits = manager.Value("d", 0.0)
    start_time = manager.Value("d", 0.0)
    count = manager.Value('i', 0)
    procs = []
    
    # Init: Monitor a file
    stamp,_ = pm.monitor_list(matched_files, n_buffers)

    # Loop and predict if changes occur
    try:
        while True:
            # monitor
            stamp, procs = pm.monitor_list(matched_files, n_buffers, stamp, procs)

            # launch prediction_process
            procs.append(
                handle_in_process(
                    prediction_process,
                    args=(data, queue, count, hits, start_time, aggregated_bytes, args,matched_files, n_buffers)
                )
            )
    except KeyboardInterrupt:
        print_data(data)
        export_extrap(data=data)
        print("-- done -- ")




def prediction_process(
    data, queue, count, hits, start_time, aggregated_bytes, args: list[str], matched_files, n_buffers) -> None:
    console = Console()
    console.print(f'[purple][PREDICTOR] (#{count.value}):[/]  Started')
    # Modify the arguments
    args.extend(['-e', 'no'])
    args.extend(['-ts', f'{start_time.value:.2f}'])
    
    # set up data
    if len(matched_files) != n_buffers:
        raise RuntimeError("Error, number of buffers does not match number of files")

    # Perform prediction
    prediction, args = run(matched_files, args)
    
    # get data
    freq = get_dominant(prediction) #just get a single dominant value
    hits = get_hits(prediction,count.value,hits)

    # save prediction results
    save_data(queue, aggregated_bytes, prediction, count, hits)
    # display results
    text = display_result(freq ,prediction ,count, aggregated_bytes)
    # data analysis to decrease window
    text, start_time.value = data_analysis(args, prediction, freq, count, hits, text)
    console.print(text)
    count.value += 1
    while not queue.empty():
        data.append(queue.get())

    probability(data)


if __name__ == "__main__":
    main()