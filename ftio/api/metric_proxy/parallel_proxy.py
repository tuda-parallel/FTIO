# from rich.progress import Progress
from ftio.api.metric_proxy.parse_proxy import parse_all
from ftio.prediction.tasks import ftio_task, ftio_task_save
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager
from ftio.prediction.helper import  print_data
# from ftio.freq.helper import MyConsole
from ftio.prediction.async_process import handle_in_process
from ftio.prediction.async_process import join_procs


metrics = parse_all("/d/sim/metric_proxy/traces/Mixed_1x8_5.json")
ranks = 32

## command line arguments
argv = ["-e", "no"]  # ["-e", "plotly"] 
# argv.extend(["-n","15"]) # finds up to n frequencies. Comment this out to go back to the default version
# ---------------------------------


parallel = False
pools = False

if parallel:
    # parallel
    manager = Manager()
    data = manager.list()
    procs = []
    try:
        if pools:
            # with Progress() as progress:
            #     task = progress.add_task("[cyan]Metrics handled", total=len(metrics.keys()))
            for metric,arrays in metrics.items():
                # with ProcessPoolExecutor(max_workers=80) as executor:
                with ProcessPoolExecutor() as executor:
                    future = executor.submit(ftio_task_save, data, metric, arrays, argv, ranks)
                        # progress.update(task, advance=1)
        else:
            for metric,arrays in metrics.items():
                procs = join_procs(procs)
                while len(procs) > 10:
                        procs = join_procs(procs)
                procs.append(handle_in_process(
                    ftio_task_save, 
                    args=(data, metric, arrays, argv, ranks)
                    )
                )
    except KeyboardInterrupt:
        print_data(data)
        print("-- done -- ")
else:
    data=[]
    save = True
    for metric,arrays in metrics.items():
        # 1 
        if save:
            ftio_task_save(data, metric, arrays, argv, ranks)
        #else 
            # 2
            ftio_task(metric, arrays, argv, ranks)
    if save:
        print_data(data)


