import pytest

from ftio.prediction.probability_analysis import find_probability

"""
Tests for class ftio/prediction/probability_analysis.py
"""


def test_find_probability():
    data = [
        {
            "dominant_freq": [0.1],
            "t_start": 0.0,
            "t_end": 10.0,
            "conf": [0.8],
            "amp": [1.0],
        },
        {
            "dominant_freq": [0.1],
            "t_start": 10.0,
            "t_end": 20.0,
            "conf": [0.8],
            "amp": [1.0],
        },
        {
            "dominant_freq": [0.1],
            "t_start": 20.0,
            "t_end": 30.0,
            "conf": [0.8],
            "amp": [1.0],
        },
    ]
    result = find_probability(data, method="step")
    assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
