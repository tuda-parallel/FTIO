import pandas as pd
import pytest
from scipy import stats

from ftio.parse.metrics import add_metric


def test_add_metric():
    b = pd.Series([100.0, 200.0, 300.0, 400.0, 500.0])
    weights = [0.0, 1.0, 2.0, 3.0, 4.0]
    ranks = 4
    run = 1

    result = add_metric(b, ranks, run, weights)

    assert result is not None
    assert len(result) == 8
    assert result[0] == ranks
    assert result[1] == run
    assert result[2] == 500.0
    assert result[3] == 100.0
    assert result[4] == 300.0
    hmean = stats.hmean([100, 200, 300, 400, 500])
    assert abs(result[5] - hmean) < 0.01
    assert abs(result[6] - 300.0) < 0.01


def test_add_metric_identical():
    b = pd.Series([50.0, 50.0, 50.0, 50.0])
    weights = [0.0, 1.0, 2.0, 3.0]
    ranks = 8
    run = 2

    result = add_metric(b, ranks, run, weights)

    assert result[2] == 50.0
    assert result[3] == 50.0
    assert result[4] == 50.0
    assert result[5] == 50.0
    assert result[6] == 50.0


def test_add_metric_zero():
    b = pd.Series([0.0, 0.0, 0.0])
    weights = [0.0, 1.0, 2.0]
    ranks = 2
    run = 0

    result = add_metric(b, ranks, run, weights)

    assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
