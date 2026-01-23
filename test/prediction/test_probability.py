import numpy as np
import pytest

from ftio.prediction.probability import Probability

"""
Tests for class ftio/prediction/probability.py
"""

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])