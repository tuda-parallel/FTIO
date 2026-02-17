import importlib.util
import os
from math import inf

import numpy as np
import pandas
import pandas as pd

TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None
if TORCH_AVAILABLE:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.stattools import adfuller, kpss
    from torch.utils.data import Dataset
else:
    raise RuntimeError(
        "Tocrch module not found. Please install it using 'make full' or 'pip install ftio[ml-libs]'."
    )

from ftio.cli import ftio_core

"""
Example Description:
This module contains the entry points for extracting data for training and prediction purpose,
the hybrid-model, the ARIMA and SARIMA models and their training and forecasting functions.
As utility it contains a custom dataset intended for the hybrid-model but was initially planned for general purpose use.

Author: Robert Alles
Copyright (c) 2026 TU Darmstadt, Germany
Date: January 2026

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""


class PositionalEncoding(nn.Module):
    """Position encoding used in the hybrid model to increase the likelihood of understanding sequential data."""

    def __init__(self, emb_dim, max_len=5555):
        """Constructor of the positional encoding.

        Args:
            emb_dim: Size of the embedding dimension
            max_len: Maximum length of sequence length that can be handled.
        """
        super().__init__()
        # Learned Positional Encoding
        self.positional_encoding = nn.Parameter(torch.zeros(1, max_len, emb_dim))

    def forward(self, x):
        """Forward method of the positional encoding.

        Args:
            x: The embedded sequence.

        Returns: The embedded sequence added to the vector of the sliced positional encoding.

        """
        # add embedded sequence + sliced positional encoding (added to device to prevent RuntimeError)
        return x + self.positional_encoding[:, : x.size(1)].to(x.device)


class BandwidthDataset(Dataset):
    """This Dataset accepts lists containing multiple partial sequences of list[ranks, bandwidth, duration, start_time]
    that combine into one complete sequence.
    The conversion of the list into a new representation in torch.tensors allows for direct training or prediction.

    """

    def __init__(self, data_list, num_parts=3):
        """Constructor of the Dataset. Convertion of data into torch.tensors.

        Args:
            data_list: Lists containing the bandwidth values of the sequence.
            num_parts: Int deciding the number of slices to be made from the sequence.
        """
        self.data = []
        self.num_parts = num_parts

        if not self.num_parts:
            self.num_parts = 3

        for seq in data_list:
            seq = torch.tensor(seq, dtype=torch.float32)
            bandwidth = seq[:, 0].unsqueeze(-1)

            # normalize per-sequence
            min_val, max_val = bandwidth.min(), bandwidth.max()
            bandwidth = (bandwidth - min_val) / (max_val - min_val + 1e-8)

            L = len(bandwidth)
            part_len = L // self.num_parts

            # split into num_parts equal parts
            parts = [
                bandwidth[i * part_len : (i + 1) * part_len]
                for i in range(self.num_parts - 1)
            ]
            parts.append(bandwidth[(self.num_parts - 1) * part_len :])
            # training input
            past = torch.cat(parts[:-1], dim=0)

            # target = last part
            future = parts[-1]
            self.data.append((past, future))

    def __len__(self):
        """Method providing the amount of datapoints inside the dataset.

        Returns: Amount of datapoints inside the dataset.

        """
        return len(self.data)

    def __getitem__(self, idx):
        """Method providing datapoint from specified index.

        Args:
            idx: Index of the specific datapoint.

        Returns: The datapoint from the specified index.

        """
        return self.data[idx]


class HybridModel(nn.Module):
    """A hybrid model leveraging transformer and long short-term memory."""

    def __init__(self, emb_dim=128, n_heads=4, ff_dim=128, num_layers=6, lstm_hidden=128):
        """Constructor of the hybrid model. Currently only supports the most important parameters.

        Args:
            emb_dim: Size of the embedding dimension
            n_heads: Amount of attention heads of transformer approach
            ff_dim: Size of the Feedforward network dimension
            num_layers: Amount of Transformer encoder layers
            lstm_hidden: Amount of hidden units in the LSTM part after transformer
        """
        super().__init__()
        self.bandwidth_embedding = nn.Linear(1, emb_dim)
        self.positional_encoding = PositionalEncoding(emb_dim)
        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=emb_dim, nhead=n_heads, dim_feedforward=ff_dim, batch_first=True
            ),
            num_layers=num_layers,
        )
        self.lstm = nn.LSTM(
            input_size=emb_dim,
            hidden_size=lstm_hidden,
            batch_first=True,
            bidirectional=True,
        )
        self.fc_bandwidth = nn.Linear(lstm_hidden * 2, 1)

    def forward(self, past_seq, prediction_length=None):
        x = self.bandwidth_embedding(past_seq)
        x = self.positional_encoding(x)
        x = self.transformer(x)
        x, _ = self.lstm(x)

        # shrink output to target length if needed
        if prediction_length is not None:
            x = x[:, -prediction_length:, :]  # take last part only

        return self.fc_bandwidth(x)


def train_hybrid_model(
    file_or_directory,
    bandwidth_cutoff=-1,
    load_state_dict_and_optimizer_state=None,
    emb_dim=128,
    n_heads=4,
    ff_dim=128,
    num_layers=3,
    epochs=10,
    lr=1e-3,
    save=False,
    additional_ftio_args=None,
) -> HybridModel:
    """Trains the hybrid model contained in this file and saves the trained model as a .pth file containing
        the model's state dict and optimizer state.


    Args:
        file_or_directory: Path to either a singular file or a directory of files to train the model with.
        bandwidth_cutoff: Any partial bandwidth sequence below this thresh hold will be cut off from the training data.
        load_state_dict_and_optimizer_state: .pth file checkpoint to continue training the model from
        emb_dim: embedded dimensions of the model
        n_heads: heads of the model
        ff_dim: feedforward dimension of the model
        num_layers: number of layers of the model
        epochs: number of epochs used to train the model
        lr: intensity of the learn rate
        save: boolean representing if the model is supposed to be saved. Doesn't affect the return value.
        additional_ftio_args: additional supported ftio arguments that aren't the initial ftio call and files

    Returns:
          HybridModel trained with provided data

    """

    # checks if file_or_directory is either just a singular file OR a path to a directory with files
    # and then saves the individual files paths
    files = []
    if os.path.isfile(file_or_directory):
        files.append(file_or_directory)
    elif os.path.isdir(file_or_directory):
        files = [
            os.path.join(file_or_directory, f)
            for f in os.listdir(file_or_directory)
            if os.path.isfile(os.path.join(file_or_directory, f))
        ]

    if not files:
        raise ValueError("No file(s) found.")

    # the initialised model
    model = HybridModel(
        emb_dim=emb_dim, n_heads=n_heads, ff_dim=ff_dim, num_layers=num_layers
    )
    load_optimizer = None

    # in case the function caller wants to train a previously trained model
    if load_state_dict_and_optimizer_state is not None:
        loaded_data = torch.load(load_state_dict_and_optimizer_state)
        model.load_state_dict(loaded_data["model_state_dict"])
        load_optimizer = loaded_data["optimizer_state_dict"]

    for x in files:
        set = []
        frequency = []
        # extraction of data through frequency analysis for darshan & json
        if x.endswith(".darshan") | x.endswith(".jsonl"):
            cmd_input = ["ftio", x]
            if additional_ftio_args is not None:
                cmd_input += additional_ftio_args
            frequency, set = extract(cmd_input=cmd_input)

        # extraction from .csv files of the sdumont traces ; not a general method to extract from any .csv file
        if x.endswith(".csv"):
            csv_file = pandas.read_csv(x)
            n = 0
            for y in csv_file["both"]:
                set.append([y])
                n = n + 1

                # max size of positional encoding of the model, limitation due to the system used for computation
                if n == 5555:
                    break

        dataset = BandwidthDataset([set], num_parts=frequency)
        load_optimizer = train_model(
            model, dataset, epochs=epochs, lr=lr, load_optimizer=load_optimizer
        )
        predict_next_sequence(model, "", only_data=(set, frequency))

    # save the model
    # currently saving it in the currently active archive
    if save:
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": load_optimizer,
            },
            "model_and_optimizer.pth",
        )

    return model


def train_model(model, dataset, epochs=3, lr=1e-3, load_optimizer=None, optimizer=None):
    """Training method for the hybrid model.

    Args:
        model: The hybrid model to be trained.
        dataset: The bandwidth dataset containing all datapoints to train the model.
        epochs: The amount of epochs used to train the model.
        lr: The learn rate of the model.
        load_optimizer: Optimizer dic in case the model was previously trained and not lose the optimizer state.
        optimizer: The optimizer to be used in the training process.

    Returns:
        The state dict of the optimizer for saving/reusing purposes.

    """
    # check if customizer needs to be loaded or initialized
    if optimizer is None:
        optimizer = optim.AdamW(model.parameters(), lr=lr)
    if load_optimizer is not None:
        optimizer.load_state_dict(load_optimizer)

    # beginning of the training loop
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=3
    )
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for past, future in dataset:
            past = past.unsqueeze(0)
            future = future.unsqueeze(0)
            # zero gradient
            optimizer.zero_grad()
            pred_future = model(past, prediction_length=future.size(1))
            # loss & backwards propagation
            loss = (0.3 * F.huber_loss(pred_future, future)) + (
                0.7 * spectral_loss(pred_future, future)
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
        # just in case to not divide by zero, it shouldn't happen but making sure it doesn't
        if len(dataset) == 0:
            a = 1
        else:
            a = len(dataset)
        scheduler.step(total_loss / a)
        # provides the total loss for some insight during the epochs IF a human is overseeing the training
        if epoch % 2 == 0:
            print(f"Last Loss: {total_loss:.4f}")
    return optimizer.state_dict()


def predict_next_sequence(
    model_or_pthfile,
    file_or_directory,
    bandwidth_cutoff=0,
    additional_ftio_args=None,
    only_data=None,
):
    """Entry point of the prediction process.

    Args:
        model_or_pthfile: Accepts either a HybridModel or a .pth file (to initialize a model) to use for the prediction.
        file_or_directory: Path to either a singular file or a directory of files to train the model with.
        bandwidth_cutoff: Any bandwidth below this thresh hold will be cut off from the data used for prediction.
        additional_ftio_args: additional supported ftio arguments that aren't the initial ftio call and files
        only_data: in the case of directly using extracted data instead of files or a path to files
    Returns:
        A list of the following form [[ranks, bandwidths], ...] where inner lists represent singular predictions.
    """

    # checks if file_or_path is either just a singular file OR a path to a directory with files
    # and then saves the individual files paths
    files = []
    if os.path.isfile(file_or_directory):
        files.append(file_or_directory)
    elif os.path.isdir(file_or_directory):
        files = [
            os.path.join(file_or_directory, f)
            for f in os.listdir(file_or_directory)
            if os.path.isfile(os.path.join(file_or_directory, f))
        ]

    # in case no files nor data was supplied
    if (not files) and (only_data is None):
        print("No files found. Aborting prediction.")
        return []

    # either use the given model or instantiate with .pth file or test with untrained model
    model = None
    if isinstance(model_or_pthfile, HybridModel):
        model = model_or_pthfile
    elif model_or_pthfile.endswith(".pth"):
        model = HybridModel(emb_dim=128, n_heads=4, ff_dim=128, num_layers=3)
        model.load_state_dict((torch.load(model_or_pthfile))["model_state_dict"])

    # prediction with an untrained model... questionable but maybe someone desires this as a test?
    if model is None:
        model = HybridModel(emb_dim=128, n_heads=4, ff_dim=128, num_layers=3)

    predictions = []

    if only_data is not None:
        set, frequency = only_data
        dataset = BandwidthDataset([set], num_parts=frequency)

        # min-max normalization
        min1, max1 = min(set)[0], max(set)[0]
        for u in range(len(set)):
            set[u][0] = (set[u][0] - min1) / (max1 - min1 + 1e-8)

        # prediction process
        prediction_current = __predict_next_trace(model, dataset)
        predictions.append(prediction_current)

        actual = []
        for c in dataset.data[0][1]:
            actual.append([c[0]])
        return predictions

    for x in files:
        set = []
        frequency = []
        # extraction of data through frequency analysis for darshan & json
        if x.endswith(".darshan") | x.endswith(".jsonl"):
            cmd_input = ["ftio", x]
            if additional_ftio_args is not None:
                cmd_input += additional_ftio_args
            frequency, set = extract(cmd_input=cmd_input)
        # extract data from traces obtained from sdumont dataset, most certainly not an approach for any .csv file
        if x.endswith(".csv"):
            csv_file = pandas.read_csv(x)
            n = 0
            for y in csv_file["both"]:
                set.append([y])
                n = n + 1

                # size limit on local machine, can be changed IF positional encoding in hybrid model is also changed
                if n == 5555:
                    break
        # min-max normalization
        min1, max1 = min(set)[0], max(set)[0]
        for u in range(len(set)):
            set[u][0] = (set[u][0] - min1) / (max1 - min1 + 1e-8)

        # prediction
        dataset = BandwidthDataset([set], num_parts=frequency)
        prediction_current = __predict_next_trace(model, dataset)
        predictions.append(prediction_current)

    return predictions


def spectral_loss(pred, target):
    """Basic spectral loss function based on one-dimensional fourier transform
    Args:
        pred: the predicted values
        target: the actual values
    """
    # pred, target: [batch, seq_len]
    pred_fft = torch.fft.rfft(pred, dim=1)
    target_fft = torch.fft.rfft(target, dim=1)
    return F.mse_loss(torch.abs(pred_fft), torch.abs(target_fft))


def __predict_next_trace(model, dataset):
    """Uses the provided hybrid model to predict the next bandwidth sequence.

    Args:
        model: the hybrid model of this file
        dataset: dataset containing the bandwidth sequences used for the prediction

    """

    model.eval()
    with torch.no_grad():
        prediction = []
        for past, future in dataset:
            # prediction
            squeezed_past = past.unsqueeze(0)
            pred_future = model(squeezed_past, prediction_length=future.size(0))
            pred_sequence = pred_future.squeeze(0).tolist()
            # only positive values are interesting
            pred_sequence = np.abs(pred_sequence)

            min_val, max_val = pred_sequence.min(), pred_sequence.max()
            pred_sequence = (pred_sequence - min_val) / (max_val - min_val + 1e-8)

            prediction.append(pred_sequence)

            # currently assumes that past and future have the same length
            # calculate MAE, MSE and RMSE
            mae = 0
            mse = 0
            for actual, predicted in zip(future, pred_sequence, strict=False):
                inner = actual.item() - predicted[0]
                mae = mae + abs(inner)
                mse = mse + (inner * inner)

            n = future.size(dim=0)
            if n == 0:
                n = 1
            mae = mae / n
            mse = mse / n

            print("Predicted Bandwidth Trace:")
            print(pred_sequence)
    return prediction


def extract(cmd_input, msgs=None) -> list:
    """Extraction method leveraging frequency analysis for the initial data in dataframe form. And calculates the amount
        of expected partial patterns

    Args:
        cmd_input: The ftio arguments in the form of a list of strings.
        msgs: ZMQ message (not used / no use intended yet)

    Returns:
        list[ n , list[bandwidth], ...]
    """
    result = []
    n = 3
    cmd_input.append("--machine_learning")
    prediction_list, args = ftio_core.main(cmd_input)
    # take only the latest for now
    if prediction_list:
        prediction = prediction_list[-1]
        b_sampled = prediction._b_sampled
        for x in b_sampled:
            result.append([x])
        # calculates the amount of partial patterns using the predicted dominant frequency of FTIO
        if (prediction.dominant_freq.size != 0) and (prediction.dominant_freq[0] != 0):
            n = int(prediction.t_end / (1 / prediction.dominant_freq[0]))
    return [n, result]


def train_arima(
    file_or_directory, max_depth=3, model_architecture="SARIMA", additional_ftio_args=None
):
    """The entry point for training the ARIMA and SARIMA models

    Args:
        file_or_directory: the file or directory to train the ARIMA model
        max_depth: the maximum depth of the ARIMA model
        model_architecture: choose between SARIMA or ARIMA architecture
        additional_ftio_args: additional supported ftio arguments that aren't the initial ftio call and files

    """
    # checks if file_or_path is either just a singular file OR a path to a directory with files
    # and then saves the individual files paths
    files = []
    if os.path.isfile(file_or_directory):
        files.append(file_or_directory)
    elif os.path.isdir(file_or_directory):
        files = [
            os.path.join(file_or_directory, f)
            for f in os.listdir(file_or_directory)
            if os.path.isfile(os.path.join(file_or_directory, f))
        ]

    # in the case of no supplied files or filepath
    if not files:
        print("No files found. Aborting prediction.")
        return []

    # use extract method for extraction of data
    predictions = []
    sequences = []
    for file in files:
        cmd_input = ["ftio", file]
        if additional_ftio_args is not None:
            cmd_input += additional_ftio_args
        n, bandwidth_sequence = extract(cmd_input=cmd_input)
        sequences.append([n, bandwidth_sequence])

    for sequence in sequences:
        # initial min-max normalization
        min_val_initial, max_val_initial = inf, -inf
        for value in sequence[1]:
            if value[0] < min_val_initial:
                min_val_initial = value[0]
            if value[0] > max_val_initial:
                max_val_initial = value[0]

        for value in sequence[1]:
            value[0] = (value[0] - min_val_initial) / (
                max_val_initial - min_val_initial + 1e-8
            )

        # split data into trainings and comparison data
        split_index = int(len(sequence[1]) / sequence[0]) * (sequence[0] - 1)
        trainings_part = sequence[1][:split_index]
        future_part = sequence[1][split_index:]
        d = 0
        # main loop to apply KPSS and ADF to find depth d
        for y in range(1):
            partial_sequence = pd.Series(
                [x[y] for x in trainings_part],
                pd.Index(np.arange(len([x[y] for x in trainings_part]), dtype="int64")),
            )

            try:
                kps = kpss(partial_sequence.dropna())[1]
            except:
                kps = 0.0

            try:
                adf = adfuller(partial_sequence.dropna())[1]
            except:
                adf = 1.0

            while d is not max_depth and kps > 0.05 > adf:
                partial_sequence = partial_sequence.diff()
                d = d + 1

                try:
                    kps = kpss(partial_sequence.dropna())[1]
                except:
                    kps = 0.0

                try:
                    adf = adfuller(partial_sequence.dropna())[1]
                except:
                    adf = 1.0
            # in case NA, INF and -INF values are introduced by differencing
            partial_sequence = partial_sequence.fillna(0.0)
            partial_sequence = partial_sequence.replace([np.inf, -np.inf], 0)

        final_model = None
        best_aic = inf
        # search grid based on AIC, limited to max p = 5 and q = 8, going deeper requires longer computing
        for p in range(5):
            for q in range(8):
                try:
                    if model_architecture == "SARIMA":
                        model = SARIMAX(
                            partial_sequence,
                            order=(p, d, q),
                            seasonal_order=(0, 0, 0, len(future_part)),
                        )
                    else:
                        model = ARIMA(partial_sequence, order=(p, d, q))
                    model = model.fit()

                    # application of the AIC
                    aic = model.aic
                    if aic < best_aic:
                        final_model = model
                        best_aic = aic
                        print("p : d : q", (p, d, q))
                # some variations will throw exceptions and warnings, this will exclude them
                except:
                    continue
        # the forecast
        prediction = final_model.forecast(len(future_part))
        # min-max normalization for uniform displaying of results to actual
        min_val, max_val = prediction.min(), prediction.max()
        prediction = (prediction - min_val) / (max_val - min_val + 1e-8)
        predictions.append(prediction)
    return predictions
