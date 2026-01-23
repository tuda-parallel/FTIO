import numpy as np
import pytest

from ftio.prediction.group import group_step, group_dbscan

"""
Tests for class ftio/prediction/group.py
"""

def testdata():
    return [
        {"dominant_freq": [0.1], "t_start": 0.0, "t_end": 10.0, "conf": [0.8], "amp": [1.0]},
        {"dominant_freq": [0.1], "t_start": 10.0, "t_end": 20.0, "conf": [0.8], "amp": [1.0]},
        {"dominant_freq": [0.5], "t_start": 20.0, "t_end": 30.0, "conf": [0.7], "amp": [1.0]},
        {"dominant_freq": [0.5], "t_start": 30.0, "t_end": 40.0, "conf": [0.7], "amp": [1.0]}
    ]


def test_group_step():
    data = testdata()
    result, num_groups = group_step(data)

    assert len(result) > 0
    assert num_groups >= 0
    for entry in result:
        assert "group" in entry


def test_group_step_different():
    data = testdata()
    result, num_groups = group_step(data)
    assert num_groups >= 1


def test_group_dbscan():
    data = testdata()
    result, num_groups = group_dbscan(data)

    assert len(result) > 0
    for entry in result:
        assert "group" in entry


def test_group_dbscan_entry():
    data = [{"dominant_freq": [0.1], "t_start": 0.0, "t_end": 10.0, "conf": [0.8], "amp": [1.0]}]
    result, num_groups = group_dbscan(data)
    assert len(result) == 1
    assert result[0]["group"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])