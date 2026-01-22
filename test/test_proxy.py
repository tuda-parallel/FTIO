"""
Functions for testing the Metric Proxy interface functionality of the ftio package.
"""

import os
import msgpack
from ftio.api.metric_proxy.proxy_zmq import handle_request

def test_proxy():
    """Test the Metric Proxy interface functionality."""
    file_path = os.path.join(os.path.dirname(__file__), "../examples/API/proxy/trace_export.msgpack")
    with open(file_path, "rb") as f:
        msg_bytes = f.read()
    reply = handle_request(msg_bytes)
    response = msgpack.unpackb(reply, raw=False)

    assert isinstance(response, list)
    assert len(response) > 0

    item = response[0]
    assert isinstance(item, dict)

    required_fields = {
        "metric",
        "dominant_freq",
        "conf",
        "amp",
        "phi",
        "t_start",
        "t_end",
        "total_bytes",
        "ranks",
        "freq",
        "top_freq",
        "n_samples",
        "wave_names",
    }

    assert required_fields.issubset(item.keys())

    top_freq = item["top_freq"]
    assert isinstance(top_freq, dict)

    required_top_freq_fields = {
        "freq",
        "conf",
        "periodicity",
        "amp",
        "phi",
    }

    assert required_top_freq_fields.issubset(top_freq.keys())