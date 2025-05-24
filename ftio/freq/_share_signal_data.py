"""
This module provides the SharedSignalData class to store and manage
common signal analysis data shared between modules such as
autocorrelation and discrete Fourier transform (DFT).

Author: Ahmad Tarraf
Copyright (c) 2025 TU Darmstadt, Germany
Date: May 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from ftio.freq.prediction import Prediction


class SharedSignalData:
    """
    A container class for sharing signal analysis data (e.g., between autocorrelation and DFT modules).

    Attributes:
        data (dict): Internal dictionary storing shared signal parameters.
    """

    def __init__(self):
        self.data = {}


    def set_data(self, b_sampled=None, freq=None, t_start=None, t_end=None, total_bytes=None):
        """
        Set shared signal analysis data.

        Args:
            b_sampled (array-like, optional): Sampled bandwidth or signal data.
            freq (float, optional): Frequency value used in analysis.
            t_start (float, optional): Start time of the signal.
            t_end (float, optional): End time of the signal.
            total_bytes (int, optional): Total number of bytes processed or analyzed.
        """
        self.data = {}

        if b_sampled is not None:
            self.data["b_sampled"] = b_sampled
        if freq is not None:
            self.data["freq"] = freq
        if t_start is not None:
            self.data["t_start"] = t_start
        if t_end is not None:
            self.data["t_end"] = t_end
        if total_bytes is not None:
            self.data["total_bytes"] = total_bytes

    def set_data_from_predicition(self, b_sampled, prediction: Prediction):
        self.data["b_sampled"] = b_sampled
        self.data["freq"] = prediction.freq
        self.data["t_start"] = prediction.t_start
        self.data["t_end"] = prediction.t_end
        self.data["total_bytes"] = prediction.total_bytes

    def get_data(self):
        """
        Get the shared data dictionary.

        Returns:
            dict: The internal data dictionary containing signal parameters.
        """
        return self.data

    def get(self, key):
        """
        Get a specific field from the shared data.

        Args:
            key (str): The key to look for in the data dictionary.

        Returns:
            The value corresponding to the key if present, else None.
        """
        return self.data.get(key, None)

    def is_empty(self):
        """
        Check whether the shared data dictionary is empty.

        Returns:
            bool: True if no data has been set, False otherwise.
        """
        return len(self.data) == 0


    def has_key(self, key):
        """
        Check if a specific key exists in the shared data.

        Args:
            key (str): The key to look for.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        return key in self.data


    def __str__(self):
        """
        Return a string summary of the current shared data.

        Returns:
            str: A string showing which keys are currently set.
        """
        return f"SharedSignalData with keys: {list(self.data.keys()) if self.data else 'None'}"