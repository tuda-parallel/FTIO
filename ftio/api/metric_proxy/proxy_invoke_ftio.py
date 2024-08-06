
import sys
import json
import numpy

from ftio.api.metric_proxy.helper import extract_data
from ftio.api.metric_proxy.parse_proxy import load_proxy_trace_stdin, parse_all
from ftio.prediction.helper import print_data
from ftio.prediction.tasks import ftio_task_save


from json import JSONEncoder

class NpArrayEncode(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.ndarray):
            numpy.nan_to_num(obj, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
            return obj.tolist()
        return JSONEncoder.default(self, obj)


def data_to_json(data: list[dict]) -> None:
    print(json.dumps(data, cls=NpArrayEncode))


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