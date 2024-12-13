import glob
from multiprocessing import Manager
from rich.console import Console
import ftio.prediction.monitor as pm
from ftio.prediction.helper import print_data, export_extrap
from ftio.prediction.async_process import handle_in_process
from ftio.prediction.probability_analysis import find_probability
from ftio.prediction.helper import get_dominant, set_hits
from ftio.api.gekkoFs.ftio_gekko import run
from ftio.prediction.analysis import display_result, save_data, window_adaptation
from ftio.prediction.shared_resources import SharedResources


def main(args: list[str] = []) -> None:

    n_buffers = 4
    args = ["-e", "plotly", "-f", "0.01"]
    # path=r'/d/github/FTIO/examples/API/gekkoFs/JSON/*.json'
    path = r"/d/github/FTIO/examples/API/gekkoFs/MSGPACK/write*.msgpack"
    # path = r"/tmp/gkfs_client_metrics/write*.msgpack"
    matched_files = glob.glob(path)

    # Init
    shared_resources = SharedResources()
    procs = []

    # Init: Monitor a file
    stamp, _ = pm.monitor_list(matched_files, n_buffers)

    # Loop and predict if changes occur
    try:
        while True:
            # monitor
            stamp, procs = pm.monitor_list(matched_files, n_buffers, stamp, procs)

            # launch prediction_process
            procs.append(
                handle_in_process(
                    prediction_process,
                    args=(
                        shared_resources,
                        args,
                        matched_files,
                        n_buffers,
                    ),
                )
            )
    except KeyboardInterrupt:
        print_data(shared_resources.data)
        export_extrap(shared_resources.data)
        print("-- done -- ")


def prediction_process(
    shared_resources: SharedResources,
    args: list[str],
    matched_files: list[str],
    n_buffers: int,
) -> None:
    console = Console()
    console.print(f"[purple][PREDICTOR] (#{shared_resources.count.value}):[/]  Started")
    # Modify the arguments
    args.extend(["-e", "no"])
    args.extend(["-ts", f"{shared_resources.start_time.value:.2f}"])

    # set up data
    if len(matched_files) != n_buffers:
        raise RuntimeError("Error, number of buffers does not match number of files")

    # Perform prediction
    prediction, parsed_args, _ = run(matched_files, args)

    # get data
    freq = get_dominant(prediction)  # just get a single dominant value
    set_hits(prediction, shared_resources)

    # save prediction results
    save_data(prediction, shared_resources)
    # display results
    text = display_result(freq, prediction, shared_resources=shared_resources)
    # data analysis to decrease window
    text = window_adaptation(parsed_args, prediction, freq, shared_resources, text)
    console.print(text)
    shared_resources.count.value += 1
    while not shared_resources.queue.empty():
        shared_resources.data.append(shared_resources.queue.get())

    _ = find_probability(shared_resources.data)


if __name__ == "__main__":
    main()
