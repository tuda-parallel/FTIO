import importlib.util
import os

import pytest

if importlib.util.find_spec("torch") is None:
    pytest.skip("Torch not available, skipping ML tests.", allow_module_level=True)

from ftio.ml.models_and_training import (
    BandwidthDataset,
    extract,
    predict_next_sequence,
    train_arima,
    train_hybrid_model,
)

"""
Tests for the active workflow (and application) of the implemented models, dataset and functions.
"""


def test_hybrid_model():
    """
    Tests the training and prediction of the hybrid-model.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    model = train_hybrid_model(
        file, epochs=10, lr=0.003, additional_ftio_args=["-e", "no"]
    )
    _ = predict_next_sequence(model, file)
    assert True


def test_hybrid_model_resume_training():
    """
    Tests the saving of the hybrid model's checkpoint and resuming of training of the model.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    model = train_hybrid_model(
        file, epochs=10, lr=0.003, save=True, additional_ftio_args=["-e", "no"]
    )
    model = train_hybrid_model(
        file,
        epochs=10,
        lr=0.003,
        load_state_dict_and_optimizer_state="model_and_optimizer.pth",
        additional_ftio_args=["-e", "no"],
    )
    _ = predict_next_sequence(model, file)
    assert True


def test_extract():
    """
    Tests the extract functionality when providing FTIO arguments.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no"]
    n, data = extract(args)
    print(data)
    print(n)
    assert True


def test_dataset():
    """
    Tests the correct initialization of the dataset.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file, "-e", "no"]
    n, data = extract(args)
    _ = BandwidthDataset([data], num_parts=n)
    assert True


def test_arima_model():
    """
    Tests the training and prediction of the ARIMA model.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    _ = train_arima(file, model_architecture="ARIMA", additional_ftio_args=["-e", "no"])
    assert True


def test_sarima_model():
    """
    Tests the training and prediction of the SARIMA model.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    _ = train_arima(file, model_architecture="SARIMA", additional_ftio_args=["-e", "no"])
    assert True
