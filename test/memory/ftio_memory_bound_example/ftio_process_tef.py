"""
Author: Ahmad Tarraf
Copyright (c) 2024-2026 TU Darmstadt, Germany
Version: 0.0.8

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import gzip
import json
import math
import sys

import numpy as np

from ftio.cli.ftio_core import core
from ftio.parse.args import parse_args


def convert_to_ftio(job) -> dict:
    operations = sorted(
        filter(lambda x: x["name"] in ["read", "write"], job["traceEvents"]),
        key=lambda x: x["ts"],
    )

    if len(operations) < 2:
        return {}

    ftio_data = {}
    job_start_ts = job["metadata"]["start_ts"]

    n_read_ops = len(list(filter(lambda x: x["name"] == "read", operations)))
    n_write_ops = len(list(filter(lambda x: x["name"] == "write", operations)))

    b_r = []
    ts_r = []
    te_r = []
    total_b_r = 0
    r_ranks = set()

    b_w = []
    ts_w = []
    te_w = []
    total_b_w = 0
    w_ranks = set()

    w_f_start, w_l_end = math.inf, 0
    r_f_start, r_l_end = math.inf, 0
    for op in operations:
        ts = op["ts"] * 1e-6
        dur = op["dur"] * 1e-6
        start = max(0, round(ts - job_start_ts, 5))
        end = round(start + max(dur, 1), 5)
        if op["name"] == "read":
            r_f_start = min(start, r_f_start)
            r_l_end = max(end, r_l_end)
            b_r.append(round(op["args"]["speed"], 5))
            ts_r.append(start)
            te_r.append(end)
            total_b_r += op["args"]["count"]
            r_ranks.add(op["tid"])
        if op["name"] == "write":
            w_f_start = min(start, w_f_start)
            w_l_end = max(end, w_l_end)
            b_w.append(round(op["args"]["speed"], 5))
            ts_w.append(start)
            te_w.append(end)
            total_b_w += op["args"]["count"]
            w_ranks.add(op["tid"])

    ftio_b_r = [0]
    ftio_t_r = [0]

    t_r = [(t, i, "ts_r") for i, t in enumerate(ts_r)] + [
        (t, i, "te_r") for i, t in enumerate(te_r)
    ]

    t_r_sorted = sorted(t_r, key=lambda x: x[0])

    for t, i, label in t_r_sorted:
        ftio_t_r.append(t)
        if label == "ts_r":
            ftio_b_r.append(ftio_b_r[-1] + b_r[i])
        else:
            ftio_b_r.append(ftio_b_r[-1] - b_r[i])

    ftio_b_w = [0]
    ftio_t_w = [0]

    t_w = [(t, i, "ts_w") for i, t in enumerate(ts_w)] + [
        (t, i, "te_w") for i, t in enumerate(te_w)
    ]

    t_w_sorted = sorted(t_w, key=lambda x: x[0])

    for t, i, label in t_w_sorted:
        ftio_t_w.append(t)
        if label == "ts_w":
            ftio_b_w.append(ftio_b_w[-1] + b_w[i])
        else:
            ftio_b_w.append(ftio_b_w[-1] - b_w[i])

    ftio_data["runtime"] = job["metadata"]["run_time"]

    if n_read_ops > 1:
        ftio_data["read"] = {}
        ftio_data["read"]["total_bytes"] = total_b_r
        ftio_data["read"]["window_duration"] = r_l_end - r_f_start
        ftio_data["read"]["number_of_ranks"] = len(r_ranks)
        ftio_data["read"]["bandwidth"] = {}
        ftio_data["read"]["bandwidth"]["b_overlap_avr"] = ftio_b_r
        ftio_data["read"]["bandwidth"]["t_overlap"] = ftio_t_r

    if n_write_ops > 1:
        ftio_data["write"] = {}
        ftio_data["write"]["total_bytes"] = total_b_w
        ftio_data["write"]["window_duration"] = w_l_end - w_f_start
        ftio_data["write"]["number_of_ranks"] = len(w_ranks)
        ftio_data["write"]["bandwidth"] = {}
        ftio_data["write"]["bandwidth"]["b_overlap_avr"] = ftio_b_w
        ftio_data["write"]["bandwidth"]["t_overlap"] = ftio_t_w

    return ftio_data


def get_main_frequencies(data: dict, trace_name: str) -> int:
    ftio_data = {
        "time": np.array(data["bandwidth"]["t_overlap"]),
        "bandwidth": np.array(data["bandwidth"]["b_overlap_avr"]),
        "total_bytes": data["total_bytes"],
        "ranks": data["number_of_ranks"],
    }
    args = parse_args(["-e", "no", "-n", "5", "-f", "-1", "--memory_limit", "1"], "ftio")
    prediction, analysis_figures = core(ftio_data, args)
    # old, does no longer work
    # freqs = list(prediction["dominant_freq"])
    # confs = list(prediction["conf"])
    #
    # New:
    # 1) get only the dominant frequency and its confidence (only 1 freq at most)
    # freq, conf = prediction.get_dominant_freq_and_conf()
    # 2) get all dominant frequencies and their confidence
    freqs, confs = prediction.dominant_freq, prediction.conf
    # 3) If you just want the top frequencies in the signal, without FTIO deciding if it is
    # dominant or not, you can use the following:
    # top_freqs = prediction.top_freqs
    # freqs, confs = top_freqs["freq"]
    periods = []
    mean_weighted_period = 0
    for freq in freqs:
        if freq == 0:
            confs = np.delete(confs, len(periods))
            continue
        period = 1 / freq
        if period / data["window_duration"] > 0.5 or confs[len(periods)] < 0.25:
            confs = np.delete(confs, len(periods))
            continue
        mean_weighted_period += period * confs[len(periods)]
        periods.append(period)
    confidence_score = np.sum(confs)
    if confidence_score == 0:
        return -1
    return int(mean_weighted_period / confidence_score)


def export_to_file(trace: str) -> None:
    with gzip.open(trace, "r") as f:
        job = json.load(f)

    ftio_data = convert_to_ftio(job)

    with open("/tmp/ftio_read.json", "w") as f:
        json.dump(ftio_data["read"], f)

    with open("/tmp/ftio_write.json", "w") as f:
        json.dump(ftio_data["write"], f)


def process(trace: str):
    if trace.endswith(".json"):
        with open(trace) as f:
            job = json.load(f)
    elif trace.endswith(".json.gz"):
        with gzip.open(trace, "r") as f:
            job = json.load(f)
    else:
        raise NotImplementedError(f"Unsupported trace format: {trace}")
    ftio_data = convert_to_ftio(job)
    ftio_res = {}
    if "write" in ftio_data:
        period = get_main_frequencies(ftio_data["write"], trace.split("/")[-1])
        if period > 0:
            ftio_res["write"] = period
    if "read" in ftio_data:
        period = get_main_frequencies(ftio_data["read"], trace.split("/")[-1])
        if period > 0:
            ftio_res["read"] = period
    print(ftio_res)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <trace.json|trace.json.gz>")
        sys.exit(1)
    process(sys.argv[1])
