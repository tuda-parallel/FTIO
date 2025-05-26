import numpy as np

from ftio.freq.prediction import Prediction


class PhaseMode:
    def __init__(self, name: str, matches: list[str]) -> None:
        self.name = name
        self.matches = matches
        self.data = []
        self.wave = np.nan
        self.t = np.array([])

    def get(self, attribute: str):
        if hasattr(self, attribute):
            return getattr(self, attribute)
        else:
            raise AttributeError(
                f"'MyClass' object has no attribute '{attribute}'"
            )

    def match(self, d: dict):
        if any(n in d["metric"] for n in self.matches):
            return True
        else:
            return False

    def add(self, d: dict) -> None:
        self.data.append(d)

    def set_time(self, t: np.ndarray) -> None:
        self.t = t

    def aggregates_waves(self, t, normed=True):
        self.wave = np.zeros(len(t))
        if self.t.size != 0:
            for i in self.data:
                self.wave = self.wave + calculate_wave(i, self.t)[0]

            if normed:
                self.wave = norm(self.wave)

    def get_wave(self, metric: str):
        wave = np.array([])
        name = ""
        if self.t.size != 0:
            for d in self.data:
                if metric in d["metric"]:
                    wave, name = calculate_wave(d, self.t)

        return (wave, name)


def calculate_wave(
    prediction: Prediction, t: np.ndarray = np.array([])
):  # -> tuple[NDArray[Any] | Any, str | LiteralString]:# -> tuple[NDArray[Any] | Any, str | LiteralString]:# -> tuple[NDArray[Any] | Any, str | LiteralString]:
    wave = np.array([])
    name = ""
    if prediction:
        n = int(
            np.floor((prediction.t_end - prediction.t_start) * prediction.freq)
        )
        if t.size == 0:
            t = np.arange(
                prediction.t_start, prediction.t_end, 1 / prediction.freq
            )

        if "top_freq" in prediction:
            wave = np.zeros_like(t)
            for j in range(0, len(prediction.top_freqs["freq"])):
                amp = prediction.top_freqs["amp"][j]
                freq = prediction.top_freqs["freq"][j]
                phi = prediction.top_freqs["phi"][j]
                wave = wave + 2 / n * amp * np.cos(2 * np.pi * freq * t + phi)
                if j < 3:
                    name += (
                        f"{2 / n *amp:.1e}*cos(2\u03c0*{freq:.2e}*t+{phi:.2e})"
                    )
                elif j == 4:
                    name += "..."
        else:
            max_conf_index = np.argmax(prediction["conf"])
            amp = prediction["amp"][max_conf_index]
            freq = prediction["dominant_freq"][max_conf_index]
            phi = prediction["phi"][max_conf_index]
            wave = 2 / n * amp * np.cos(2 * np.pi * freq * t + phi)
            name += f"{2 / n *amp:.1e}*cos(2\u03c0*{freq:.2e}*t+{phi:.2e})"
    return (wave, name)


def norm(wave: np.ndarray) -> np.ndarray:
    max_value = np.max(np.abs(wave))
    normed_wave = wave / max_value if max_value > 0 else wave
    return normed_wave
