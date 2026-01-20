import numpy as np
import pytest

from ftio.prediction.probability import Probability
from ftio.prediction.helper import (
    get_dominant,
    get_dominant_and_conf,
    print_data,
    format_jsonl,
)
from ftio.prediction.group import group_step, group_dbscan
from ftio.prediction.probability_analysis import find_probability
from ftio.prediction.unify_predictions import merge_core
from ftio.freq.prediction import Prediction
from ftio.prediction.shared_resources import SharedResources

# Tests for prediction/probability.py
def test_init():
    prob = Probability(freq_min=0.1, freq_max=0.5)

    assert prob.freq_min == 0.1
    assert prob.freq_max == 0.5
    assert prob.p_periodic == 0
    assert prob.p_freq == 0
    assert prob.p_freq_given_periodic == 0
    assert prob.p_periodic_given_freq == 1


def test_init_custom():
    prob = Probability(
        freq_min=0.2,
        freq_max=0.8,
        p_periodic=0.5,
        p_freq=0.3,
        p_freq_given_periodic=0.7,
        p_periodic_given_freq=0.9
    )

    assert prob.freq_min == 0.2
    assert prob.freq_max == 0.8
    assert prob.p_periodic == 0.5
    assert prob.p_freq == 0.3
    assert prob.p_freq_given_periodic == 0.7
    assert prob.p_periodic_given_freq == 0.9


def test_set():
    prob = Probability(freq_min=0.1, freq_max=0.5)
    prob.set(p_periodic=0.6, p_freq=0.4, p_freq_given_periodic=0.8, p_periodic_given_freq=0.7)

    assert prob.p_periodic == 0.6
    assert prob.p_freq == 0.4
    assert prob.p_freq_given_periodic == 0.8
    assert prob.p_periodic_given_freq == 0.7


def test_set_nan():
    prob = Probability(freq_min=0.1, freq_max=0.5, p_periodic=0.5, p_freq=0.3)
    prob.set(p_periodic=np.nan, p_freq=0.7)

    assert prob.p_periodic == 0.5
    assert prob.p_freq == 0.7


def test_freq_in_range():
    prob = Probability(freq_min=0.1, freq_max=0.5)
    assert prob.get_freq_prob(0.1) is True
    assert prob.get_freq_prob(0.3) is True
    assert prob.get_freq_prob(0.5) is True


def test_freq_in_range_edge():
    prob = Probability(freq_min=0.0, freq_max=1.0)

    assert prob.get_freq_prob(0.0) is True
    assert prob.get_freq_prob(1.0) is True
    assert prob.get_freq_prob(-0.1) is False
    assert prob.get_freq_prob(1.1) is False


def test_display():
    prob = Probability(freq_min=0.1, freq_max=0.5, p_periodic=0.5)
    prob.display()
    prob.display(prefix="[TEST]")


#tests for prediction/helper.py

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


#tests for prediction/group.py

def test_group_step():
    data = [
        {"dominant_freq": [0.1], "t_start": 0.0, "t_end": 10.0, "conf": [0.8], "amp": [1.0]},
        {"dominant_freq": [0.1], "t_start": 10.0, "t_end": 20.0, "conf": [0.8], "amp": [1.0]},
        {"dominant_freq": [0.5], "t_start": 20.0, "t_end": 30.0, "conf": [0.7], "amp": [1.0]},
        {"dominant_freq": [0.5], "t_start": 30.0, "t_end": 40.0, "conf": [0.7], "amp": [1.0]}
    ]

    result, num_groups = group_step(data)

    assert len(result) > 0
    assert num_groups >= 0
    for entry in result:
        assert "group" in entry


def test_group_step_different():
    data = [
        {"dominant_freq": [0.1], "t_start": 0.0, "t_end": 10.0, "conf": [0.8], "amp": [1.0]},
        {"dominant_freq": [0.5], "t_start": 10.0, "t_end": 20.0, "conf": [0.8], "amp": [1.0]},
        {"dominant_freq": [1.0], "t_start": 20.0, "t_end": 30.0, "conf": [0.8], "amp": [1.0]}
    ]

    result, num_groups = group_step(data)
    assert num_groups >= 1


def test_group_dbscan():
    data = [
        {"dominant_freq": [0.1], "t_start": 0.0, "t_end": 10.0, "conf": [0.8], "amp": [1.0]},
        {"dominant_freq": [0.11], "t_start": 10.0, "t_end": 20.0, "conf": [0.8], "amp": [1.0]},
        {"dominant_freq": [0.5], "t_start": 20.0, "t_end": 30.0, "conf": [0.7], "amp": [1.0]},
        {"dominant_freq": [0.51], "t_start": 30.0, "t_end": 40.0, "conf": [0.7], "amp": [1.0]}
    ]
    result, num_groups = group_dbscan(data)

    assert len(result) > 0
    for entry in result:
        assert "group" in entry


def test_group_dbscan_entry():
    data = [{"dominant_freq": [0.1], "t_start": 0.0, "t_end": 10.0, "conf": [0.8], "amp": [1.0]}]
    result, num_groups = group_dbscan(data)
    assert len(result) == 1
    assert result[0]["group"] == 0


# Tests for prediction/probability_analysis.py

def test_find_probability():
    data = [
            {"dominant_freq": [0.1], "t_start": 0.0, "t_end": 10.0, "conf": [0.8], "amp": [1.0]},
            {"dominant_freq": [0.1], "t_start": 10.0, "t_end": 20.0, "conf": [0.8], "amp": [1.0]},
            {"dominant_freq": [0.1], "t_start": 20.0, "t_end": 30.0, "conf": [0.8], "amp": [1.0]},
    ]
    result = find_probability(data, method="step")
    assert isinstance(result, list)


# Tests for prediction/unify_predictions.py

def test_merge_predictions():
    pred = Prediction(transformation="dft")
    pred.dominant_freq = np.array([0.1, 0.2, 0.3])
    pred.conf = np.array([0.7, 0.8, 0.6])
    pred.amp = np.array([1.0, 2.0, 0.5])
    pred.phi = np.array([0.0, 0.1, 0.2])

    pred2= Prediction(transformation="autocorrelation")
    pred2.dominant_freq = np.array([0.2])
    pred2.conf = np.array([0.85])
    pred2.amp = np.array([1.5])
    pred2.phi = np.array([0.05])
    pred2.candidates = np.array([4.9, 5.0, 5.1])  # ~1/0.2 = 5 sec period

    merged, text = merge_core(pred, pred2, freq=10.0, text="")

    assert isinstance(merged, Prediction)
    assert isinstance(text, str)


# Tests for  prediction/shared_resources.py

def test_shared_resources_init():
    sr = SharedResources()

    assert sr.queue is not None
    assert sr.data is not None
    assert sr.aggregated_bytes.value == 0.0
    assert sr.hits.value == 0.0
    assert sr.start_time.value == 0.0
    assert sr.count.value == 0

    sr.shutdown()


def test_shared_resources_queue():
    sr = SharedResources()

    sr.queue.put({"test": "data"})
    assert not sr.queue.empty()

    item = sr.queue.get()
    assert item == {"test": "data"}
    assert sr.queue.empty()

    sr.shutdown()


def test_shared_resources_update():
    sr = SharedResources()

    sr.aggregated_bytes.value = 1337.0
    sr.hits.value = 5.0
    sr.count.value = 10

    assert sr.aggregated_bytes.value == 1337.0
    assert sr.hits.value == 5.0
    assert sr.count.value == 10

    sr.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])