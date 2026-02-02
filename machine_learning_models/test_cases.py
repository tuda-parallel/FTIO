from machine_learning_models import *

"""
Tests for the active workflow (and application) of the implemented models, dataset and functions.
"""


def test_hybrid_model():
    """
    Tests the training and prediction of the hybrid-model.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    model = train_hybrid_model(file, epochs=10, lr=0.003)
    prediction = predict_next_sequence(model, file)
    assert True


def test_hybrid_model_resume_training():
    """
    Tests the saving of the hybrid model's checkpoint and resuming of training of the model.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    model = train_hybrid_model(file, epochs=10, lr=0.003, save=True)
    model = train_hybrid_model(
        file,
        epochs=10,
        lr=0.003,
        load_state_dict_and_optimizer_state="model_and_optimizer.pth",
    )
    prediction = predict_next_sequence(model, file)
    assert True


def test_extract():
    """
    Tests the extract functionality when providing FTIO arguments.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file]
    n, data = extract(args)
    assert True


def test_dataset():
    """
    Tests the correct initialization of the dataset.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    args = ["ftio", file]
    n, data = extract(args)
    dataset = BandwidthDataset([data], num_parts=n)
    assert True


def test_arima_model():
    """
    Tests the training and prediction of the ARIMA model.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    prediction = train_arima(file, model_architecture="ARIMA")
    assert True


def test_sarima_model():
    """
    Tests the training and prediction of the SARIMA model.
    """
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    prediction = train_arima(file, model_architecture="SARIMA")
    assert True
