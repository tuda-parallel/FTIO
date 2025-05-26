import numpy as np


class Prediction:
    """
    A class to store and manipulate prediction data related to frequency analysis.

    Attributes:
        source (str): The name or type of transformation used to generate predictions.
        dominant_freq (np.ndarray): Array of dominant frequencies identified in the data.
        conf (np.ndarray): Confidence values associated with each dominant frequency.
        amp (np.ndarray): Amplitudes corresponding to each dominant frequency.
        phi (np.ndarray): Phase angles for each dominant frequency.
        t_start (float): Start time index or timestamp for the prediction interval.
        t_end (float): End time index or timestamp for the prediction interval.
        total_bytes (int): Total number of bytes processed or considered.
        sampled_freq (float): Sampling frequency (samples per unit time) used for the data.
        ranks (int): Number of ranks or parallel processes involved.
        n_samples (int): Number of samples used in the prediction.
        top_freqs (dict): Dictionary storing top frequencies and associated metadata.
        candidates (np.ndarray): Array of candidates used in autocorrelation or other analysis.
    """

    def __init__(
        self,
        transformation: str = "",
        t_start: float = 0,
        t_end: float = 0,
        total_bytes: int = 0,
        sampled_freq: float = 0,
        ranks: int = 0,
        n_samples=0,
    ):
        self._source = transformation
        self._dominant_freq = np.array([])
        self._conf = np.array([])
        self._amp = np.array([])
        self._phi = np.array([])
        self._t_start = t_start
        self._t_end = t_end
        self._total_bytes = total_bytes
        self._freq = sampled_freq
        self._ranks = ranks
        self._n_samples = n_samples
        self._top_freqs = {}
        self._candidates = np.array([])

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        self._source = str(value)

    @property
    def dominant_freq(self):
        return self._dominant_freq

    @dominant_freq.setter
    def dominant_freq(self, value):
        # if single numeric, convert to np.array([value])
        if np.isscalar(value):
            value = np.array([value])
        elif isinstance(value, list):
            value = np.array(value)
        if not isinstance(value, np.ndarray):
            raise TypeError(
                "dominant_freq must be a numpy ndarray, list convertible to ndarray, or a numeric scalar"
            )
        self._dominant_freq = value

    @property
    def conf(self):
        return self._conf

    @conf.setter
    def conf(self, value):
        # same logic as dominant_freq
        if np.isscalar(value):
            value = np.array([value])
        elif isinstance(value, list):
            value = np.array(value)
        if not isinstance(value, np.ndarray):
            raise TypeError(
                "conf must be a numpy ndarray, list convertible to ndarray, or a numeric scalar"
            )
        self._conf = value

    @property
    def amp(self):
        return self._amp

    @amp.setter
    def amp(self, value):
        if isinstance(value, list):
            value = np.array(value)
        if not isinstance(value, np.ndarray):
            raise TypeError(
                "amp must be a numpy ndarray or list convertible to ndarray"
            )
        self._amp = value

    @property
    def phi(self):
        return self._phi

    @phi.setter
    def phi(self, value):
        if isinstance(value, list):
            value = np.array(value)
        if not isinstance(value, np.ndarray):
            raise TypeError(
                "phi must be a numpy ndarray or list convertible to ndarray"
            )
        self._phi = value

    @property
    def t_start(self):
        return self._t_start

    @t_start.setter
    def t_start(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError("t_start must be a number")
        self._t_start = value

    @property
    def t_end(self):
        return self._t_end

    @t_end.setter
    def t_end(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError("t_end must be a number")
        self._t_end = value

    @property
    def total_bytes(self):
        return self._total_bytes

    @total_bytes.setter
    def total_bytes(self, value):
        if not isinstance(value, int):
            raise TypeError("total_bytes must be an int")
        self._total_bytes = value

    @property
    def sampled_freq(self):
        return self._freq

    @sampled_freq.setter
    def sampled_freq(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError("sampled_freq must be a number")
        self._freq = value

    @property
    def ranks(self):
        return self._ranks

    @ranks.setter
    def ranks(self, value):
        if not isinstance(value, int):
            raise TypeError("ranks must be an int")
        self._ranks = value

    @property
    def n_samples(self):
        return self._n_samples

    @n_samples.setter
    def n_samples(self, value):
        if not isinstance(value, int):
            raise TypeError("n_samples must be an int")
        self._n_samples = value

    @property
    def top_freqs(self):
        return self._top_freqs

    @top_freqs.setter
    def top_freqs(self, value):
        if not isinstance(value, dict):
            raise TypeError("top_freqs must be a dict")
        self._top_freqs = value

    @property
    def candidates(self):
        return self._candidates

    @candidates.setter
    def candidates(self, value):
        if isinstance(value, list):
            value = np.array(value)
        if not isinstance(value, np.ndarray):
            raise TypeError(
                "candidates must be a numpy ndarray or list convertible to ndarray"
            )
        self._candidates = value

    def get(self, key: str):
        """
        Retrieve the value for a given attribute.

        Args:
            key (str): Attribute name.

        Returns:
            Any: Value of the attribute or None if not found.
        """
        return getattr(self, key, None)

    def set(self, key: str, value):
        """
        Set the value of a given attribute.

        Args:
            key (str): Attribute name.
            value (Any): Value to set.

        Raises:
            AttributeError: If the attribute is invalid.
        """
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise AttributeError(f"Invalid attribute: {key}")

    def set_from_dict(self, data: dict):
        """
        Set multiple attributes from a dictionary.

        Args:
            data (dict): Keys are attribute names, values are the new values.

        Raises:
            AttributeError: If any key is not a valid attribute.
        """
        for key, value in data.items():
            self.set(key, value)

    def get_dominant_freq_and_conf(self) -> tuple[float, float]:
        """
        Return the dominant frequency and its corresponding confidence.

        Returns:
            tuple of float:
                - Dominant frequency with the highest confidence.
                - Associated confidence value.
                Returns (np.nan, np.nan) if no data is available.
        """
        out_freq = np.nan
        out_conf = np.nan
        if len(self._dominant_freq) > 0:
            dominant_index = self.get_dominant_index()
            if dominant_index is not None:
                out_freq = self._dominant_freq[dominant_index]
                out_conf = self._conf[dominant_index]
        return out_freq, out_conf

    def get_dominant_freq(self) -> float:
        """
        Return the dominant frequency

        Returns:
            tuple of float:
                - Dominant frequency with the highest confidence.
        """
        out_freq = np.nan
        if len(self._dominant_freq) > 0:
            dominant_index = self.get_dominant_index()
            if dominant_index is not None:
                out_freq = self._dominant_freq[dominant_index]
        return out_freq

    def get_dominant_freq_and_index(self) -> tuple[float, float]:
        """
        Return the dominant frequency and its index in the list.

        Returns:
            tuple of float:
                - Dominant frequency with the highest confidence.
                - Index of the dominant frequency.
                Returns (np.nan, np.nan) if no data is available.
        """
        out_freq = np.nan
        dominant_index = np.nan
        if len(self._dominant_freq) > 0:
            dominant_index = self.get_dominant_index()
            if dominant_index is not None:
                out_freq = self._dominant_freq[dominant_index]
        return out_freq, dominant_index

    def get_dominant_freq_amp_phi(self):
        dominant_index = self.get_dominant_index()
        if dominant_index is not None:
            return (
                self._dominant_freq[dominant_index],
                self._amp[dominant_index],
                self._phi[dominant_index],
            )
        else:
            return np.nan, np.nan, np.nan

    def get_dominant_index(self):
        # or use conf?
        if self._amp is not None and len(self._amp) > 0:
            return np.argmax(self._amp)
        return None

    def is_empty(self):
        """
        Check if the prediction is empty.

        Returns:
            bool: True if source is empty, False otherwise.
        """
        return not self.source

    def to_dict(self):
        """
        Return a dictionary representation of the Prediction object.

        Returns:
            dict: A copy of all relevant instance attributes.
        """
        return {
            "source": self._source,
            "dominant_freq": self._dominant_freq,
            "conf": self._conf,
            "amp": self._amp,
            "phi": self._phi,
            "t_start": self.t_start,
            "t_end": self._t_end,
            "total_bytes": self._total_bytes,
            "sampled_freq": self._freq,
            "ranks": self._ranks,
            "n_samples": self._n_samples,
            "top_freqs": self._top_freqs,
            "candidates": self._candidates,
        }

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()

    def __add__(self, other):
        """
        Overload + operator to return a list of dicts of the predictions.

        Args:
            other (Prediction or list): Another prediction instance or list.

        Returns:
        list: Combined list of prediction dictionaries.

        Raises:
            TypeError: If operand type is unsupported.
        """
        if isinstance(other, Prediction):
            return [self.to_dict(), other.to_dict()]
        elif isinstance(other, list):
            return other + [self.to_dict()]
        else:
            raise TypeError(
                f"Unsupported operand type(s) for +: 'Prediction' and '{type(other).__name__}'"
            )

    def __bool__(self):
        """
        Boolean check for non-empty prediction.

        Returns:
            bool: True if not empty, else False.
        """
        return not self.is_empty()
