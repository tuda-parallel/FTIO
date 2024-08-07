import sys

# from rich.progress import Progress
from ftio.api.metric_proxy.parse_proxy import parse_all,get_all_metrics, filter_deriv
from ftio.api.metric_proxy.helper import extract_data
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
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager
from ftio.prediction.helper import print_data


# from ftio.freq.helper import MyConsole
from ftio.prediction.async_process import handle_in_process
from ftio.prediction.async_process import join_procs


def main(argv):
    # ---------------------------------
    # Modification area
    # ---------------------------------
    parallel = False
    pools = False
    show = False  # shows the results from FTIO
    proxy = True

    if proxy:
        mp = MetricProxy()
        # # Get a LIST of all JOBs
        jobs = mp.jobs()
        # Get a JSONL for this JOB
        job_id = jobs[0]["jobid"]
        jsonl = mp.trace(job_id)
        metrics = filter_deriv(jsonl,deriv_and_not_deriv=False)

        # Workaround: proxy needs to be running
        # metrics = get_all_metrics('4195024897')
    ranks = 32

    # command line arguments
    argv = ["-e", "no"]  # ["-e", "plotly"]
    # finds up to n frequencies. Comment this out to go back to the default version
    argv.extend(["-n", "10"])
    # ---------------------------------

    # plot_timeseries_metrics(metrics)

    if parallel:
        execute_parallel(metrics, argv, ranks, show, pools)
    else:
        execute(metrics, argv, ranks, show)


def execute_parallel(
    metrics: dict, argv: list, ranks: int, show: bool, pools: bool
) -> None:
    # parallel
    manager = Manager()
    data = manager.list()
    procs = []
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
        else:
            for metric, arrays in metrics.items():
                procs = join_procs(procs)
                while len(procs) > 10:
                    procs = join_procs(procs)
                procs.append(
                    handle_in_process(
                        ftio_task_save, args=(data, metric, arrays, argv, ranks, show)
                    )
                )
    except KeyboardInterrupt:
        print_data(data)
        print("-- done -- ")
        exit()

    # print_data(data)
    heatmap(data)
    df = extract_data(data)
    scatter2D(df)
    print("-- done -- ")


def execute(metrics: dict, argv: list, ranks: int, show: bool):
    data = []
    save = True
    for metric, arrays in metrics.items():
        if save:
            # save stuff in queue
            ftio_task_save(data, metric, arrays, argv, ranks, show)
        else:
            # skip saving
            ftio_task(metric, arrays, argv, ranks, show)
    if save:
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
        exit()
        density_heatmap(data)
        heatmap_2(data)


if __name__ == "__main__":
    main(sys.argv)
