import numpy as np
import pytest

from ftio.freq.prediction import Prediction
from ftio.prediction.helper import (
    get_dominant,
    get_dominant_and_conf,
    print_data,
    format_jsonl,
)

"""
Tests for class ftio/prediction/helper.py
"""

def test_get_dominant():
    pred = Prediction()
    pred.dominant_freq = np.array([0.1, 0.2, 0.3])
    pred.conf = np.array([0.5, 0.8, 0.3])
    pred.amp = np.array([1.0, 2.0, 0.5])

    result = get_dominant(pred)

    assert result == 0.2


def test_get_dominant_empty():
    pred = Prediction()
    pred.dominant_freq = np.array([])
    pred.conf = np.array([])
    pred.amp = np.array([])
    result = get_dominant(pred)

    assert np.isnan(result)


def test_get_dominant_and_conf():
    pred = Prediction()
    pred.dominant_freq = np.array([0.1, 0.2, 0.3])
    pred.conf = np.array([0.5, 0.8, 0.3])
    pred.amp = np.array([1.0, 2.0, 0.5])

    freq, conf = get_dominant_and_conf(pred)

    assert freq == 0.2
    assert conf == 0.8


def test_get_dominant_and_conf_empty():
    pred = Prediction()

    freq, conf = get_dominant_and_conf(pred)

    assert np.isnan(freq)
    assert np.isnan(conf)


def test_print_data(capsys):
    data = [
        {"dominant_freq": [0.1], "conf": 0.8},
        {"dominant_freq": [0.2], "conf": 0.9},
    ]
    print_data(data)
    captured = capsys.readouterr()

    assert "Data collected is:" in captured.out
    assert "dominant_freq" in captured.out


def test_format_jsonl():
    data = [
        {
            "dominant_freq": np.array([0.1]),
            "conf": np.array([0.8]),
            "amp": np.array([1.0]),
            "ranks": 4,
        }
    ]

    result, ranks = format_jsonl(data)

    assert "Frequency" in result
    assert "Period" in result
    assert '"Processes":4' in result
    assert ranks == 4


def test_format_jsonl_empty():
    data = []
    result, ranks = format_jsonl(data)

    assert result == ""
    assert np.isnan(ranks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])