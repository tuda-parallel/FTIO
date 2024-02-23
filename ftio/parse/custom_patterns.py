def convert():

    pattern = {
        "avg_thruput_mib": r"avg_thruput_mib:\s+\[([\d.\d,\s]+)\]",
        "end_t_micro": r"end_t_micro:\s+\[([\d,\s]+)\]",
        "start_t_micro": r"start_t_micro:\s+\[([\d,\s]+)\]",
        # "req_size": r"req_size:\s+\[([\d,\s]+)\]",
        "total_bytes": r"total_bytes:\s+(\d+)",
        "total_iops": r"total_iops:\s+(\d+)",
        }

        # Define map according to Sample class, along with the scale if any
    map = {
        "bandwidth": {
            "b_rank_avr": ("avg_thruput_mib",1.07*1e+6),
            "t_rank_e": ("end_t_micro", 1e-3),
            "t_rank_s": ("start_t_micro", 1e-3)
            },
        # "max_transfersize_over_ranks": "req_size",
        "total_bytes": "total_bytes",
        "max_io_ops_per_rank": "total_iops"
        }
    return pattern, map