import sys
from ftio.api.metric_proxy.helper import extract_data
from ftio.api.metric_proxy.parse_proxy import load_proxy_trace_stdin, parse_all
from ftio.prediction.helper import print_data
from ftio.api.metric_proxy.helper import data_to_json
from ftio.prediction.tasks import ftio_task_save





def main():
    argv = sys.argv[1:]
    metrics = load_proxy_trace_stdin(deriv_and_not_deriv=False)
    ranks = 32

    # Make sure we do no plots
    argv.extend(["-e", "no"])

    data = []

    for metric, arrays in metrics.items():
        ftio_task_save(data, metric, arrays, argv, ranks, False)
    data_to_json(data)


if __name__ == "__main__":
    main()