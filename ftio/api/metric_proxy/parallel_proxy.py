from multiprocessing.managers import ListProxy
import sys
import numpy as np
from multiprocessing import Manager, cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed

# from rich.progress import Progress
from ftio.api.metric_proxy.parse_proxy import parse_all,get_all_metrics, filter_metrics
from ftio.api.metric_proxy.helper import extract_data, create_process_bar
from ftio.api.metric_proxy.proxy_analysis import phases, phases_and_timeseries
from ftio.api.metric_proxy.plot_proxy import (
    heatmap,
    scatter2D,
    scatter,
    heatmap_2,
    density_heatmap,
    plot_timeseries_metrics,
)
from ftio.api.metric_proxy.proxy_cluster import optics,dbscan
from ftio.api.metric_proxy.req import MetricProxy
from ftio.prediction.tasks import ftio_task, ftio_task_save
from ftio.prediction.helper import print_data
from ftio.freq.helper import MyConsole


CONSOLE = MyConsole()
CONSOLE.set(True)


def main(file:str = ""):
    # ---------------------------------
    # Modification area
    # ---------------------------------
    parallel = True
    pools = False
    show = False  # shows the results from FTIO
    argv = ["-e","no"]
    # argv = ["-e", "mat"]  # ["-e", "plotly"]
    # # finds up to n frequencies. Comment this out to go back to the default version
    # argv.extend(["-n", "10"])
    # ---------------------------------

    if not file:
        mp = MetricProxy()
        # # Get a LIST of all JOBs
        jobs = mp.jobs()
        # Get a JSONL for this JOB
        job_id = jobs[0]["jobid"]
        jsonl = mp.trace(job_id)
        metrics = filter_metrics(jsonl,filter_deriv=True)

        # Workaround: proxy needs to be running
        # metrics = get_all_metrics('4195024897')
    else:
        # file = "/d/github/FTIO/ftio/api/metric_proxy/traces/jb_traces/WACOM_PROCESS_BASED_json/wacommplusplus.36procs.trace.json"
        # file = "/d/sim/metric_proxy/traces/Mixed_1x8_5.json"
        metrics = parse_all(file, filter_deriv=True,exclude=["size","hits"], scale_t=1e-3)
        

    ranks = 32

    _ = plot_timeseries_metrics(metrics, 2000,500)

    if parallel:
        data = execute_parallel(metrics, argv, ranks, show, pools)
    else:
        data = execute(metrics, argv, ranks, show)
    
    post(data, metrics, argv)


def execute_parallel(
    metrics: dict, argv: list, ranks: int, show: bool = False, pools: bool = False
)  :
    # parallel
    manager = Manager()
    data = manager.list()
    counter = 0
    total_files = len(metrics)
    progress = create_process_bar(total_files)
    task = progress.add_task("[green]Processing files", total=total_files)
    with progress:
        try:
            if pools:
                # with Progress() as progress:
                #     task = progress.add_task("[cyan]Metrics handled", total=len(metrics.keys()))
                for metric, arrays in metrics.items():
                    # with ProcessPoolExecutor(max_workers=80) as executor:
                    with ProcessPoolExecutor() as executor:
                        _ = executor.submit(
                            ftio_task_save, data, metric, arrays, argv, ranks, show
                        )
                        # progress.update(task, advance=1)
                        counter += 1
                        progress.update(task, completed=counter)
            else: #use futures
                with ProcessPoolExecutor(max_workers=cpu_count()-2) as executor:
                    futures = {
                            executor.submit(
                                ftio_task_save, data, metric, arrays, argv, ranks, show): metric 
                            for metric, arrays in metrics.items()
                        }
                    for future in as_completed(futures):
                        counter += 1
                        progress.update(task, completed=counter)
        except KeyboardInterrupt:
            print_data(data)
            print("-- done -- ")
            exit()

    return data


def execute(metrics: dict, argv: list, ranks: int, show: bool):
    data = []
    save = True
    check = True

    error_counter = 0 
    counter = 0
    total_files = len(metrics)
    progress = create_process_bar(total_files)
    
    with progress:
        task = progress.add_task("[green]Processing files", total=total_files)
        for metric, arrays in metrics.items():
            if check:
                decreasing_order = np.all(arrays[1][-1] >= arrays[1][1])
                # negative = np.all(arrays[0] <= 0)
                if not decreasing_order: #or not  negative:
                    error_counter += 1
                    # err = "[bold red] Negative metric" if not negative else "[bold yellow] time not decreasing"
                    err = "[bold yellow] time not decreasing"
                    CONSOLE.print(f"[bold red]- {error_counter}. Error in {metric}:{err}[/]")
                    continue
            if save:
                # save stuff in queue, data is non empty
                ftio_task_save(data, metric, arrays, argv, ranks, show)
            else:
                # skip saving
                ftio_task(metric, arrays, argv, ranks, show)
            counter += 1
            progress.update(task, completed=counter)

    return data 

def post(data, metrics, argv):
    if data:
        # print_data(data)
        phases(data, argv)
        phases_and_timeseries(metrics, data, argv)
        df = extract_data(data)
        heatmap(data)
        scatter2D(df)
        scatter(
            df, x="Phi", y="Dominant Frequency", color="Confidence", symbol="Metric"
        )
        _ = optics(df,"Phi","Dominant Frequency")
        _ = dbscan(df,"Phi","Dominant Frequency")
        # exit()
        density_heatmap(data)
        heatmap_2(data)
    else:
        CONSOLE.print("[bold red] No data[/]")

if __name__ == "__main__":
    
    # file = "/d/github/FTIO/ftio/api/metric_proxy/traces/alberto_unito/bench_8x144.json"
    # file = "/d/github/FTIO/ftio/api/metric_proxy/traces/jb_traces/WACOM_PROCESS_BASED_json/wacommplusplus.36procs.trace.json"
    # file = "/d/sim/metric_proxy/traces/Mixed_1x8_5.json"file = /d/github/FTIO/ftio/api/metric_proxy/new_traces/imbio.json"
    file = "/d/github/FTIO/ftio/api/metric_proxy/new_traces/imbio.json"
    main(file)
    

    # proxy
    # main()
