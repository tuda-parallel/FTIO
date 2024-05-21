pattern = {
    "avg_thruput_mib": r"avg_thruput_mib:\s+\[([\d.\d,\s]+)\]",
    "end_t_micro": r"end_t_micro:\s+\[([\d,\s]+)\]",
    "start_t_micro": r"start_t_micro:\s+\[([\d,\s]+)\]",
    "total_bytes": r"total_bytes:\s+(\d+)",
    }

# Define map according to sample.py class, along with the scale if any:
# ftio_field: ("custom_name", scale)
# ftio unit are default in bytes, b/s, ...
# scale applies ftio_field = custom_name*scale
translate = {
    "bandwidth": {
        "b_rank_avr": ("avg_thruput_mib",1.07*1e+6),
        "t_rank_e": ("end_t_micro", 1e-3),
        "t_rank_s": ("start_t_micro", 1e-3)
        },
    "total_bytes": "total_bytes",
    }
