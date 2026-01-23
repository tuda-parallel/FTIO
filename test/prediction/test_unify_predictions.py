import pytest
import numpy as np

from ftio.prediction.unify_predictions import merge_core
from ftio.freq.prediction import Prediction

"""
Tests for class ftio/prediction/unify_predictions.py
"""

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])