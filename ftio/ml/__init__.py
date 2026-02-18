"""
FTIO Machine Learning module.

This module provides machine learning models for I/O bandwidth prediction:
- HybridModel: Transformer-LSTM hybrid model
- BandwidthDataset: Custom dataset for bandwidth sequences
- train_hybrid_model: Training function for the hybrid model
- predict_next_sequence: Prediction function for the hybrid model
- train_arima: Training function for ARIMA/SARIMA models
- extract: Data extraction function using FTIO frequency analysis

Author: Robert Alles
Editor: Ahmad Tarraf
Copyright (c) 2026 TU Darmstadt, Germany
Date: January 2026

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

# Re-export for backward compatibility with models_and_training imports
from ftio.ml.hybrid_model import (
    BandwidthDataset,
    HybridModel,
    PositionalEncoding,
    spectral_loss,
)
from ftio.ml.hybrid_training import (
    extract,
    predict_next_sequence,
    train_hybrid_model,
    train_model,
)
from ftio.ml.arima import train_arima

__all__ = [
    "BandwidthDataset",
    "HybridModel",
    "PositionalEncoding",
    "spectral_loss",
    "extract",
    "predict_next_sequence",
    "train_hybrid_model",
    "train_model",
    "train_arima",
]