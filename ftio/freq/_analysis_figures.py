import numpy as np
from argparse import Namespace
from ftio.freq.freq_html import create_html


class AnalysisFigures:
    def __init__(self, args:Namespace=None, b=None, t=None, b_sampled=None, t_sampled=None,
                 freqs=None, amp=None, phi=None, conf=None, ranks=None, scales = None, coefficients=None):
        self.set_bulk(args, b, t, b_sampled, t_sampled, freqs, amp, phi, conf, ranks, scales, coefficients)
        self.figures = []
        self.figure_titles = []

    def set_bulk(self, args:Namespace=None, b=None, t=None, b_sampled=None, t_sampled=None,
                 freqs=None, amp=None, phi=None, conf=None, ranks=None, scales = None, coefficients=None):
        if args is not None:
            self.args = args
        if b is not None:
            self.b = b
        if t is not None:
            self.t = t
        if b_sampled is not None:
            self.b_sampled = b_sampled
        if t_sampled is not None:
            self.t_sampled = t_sampled
        if freqs is not None:
            self.freqs = freqs
        if amp is not None:
            self.amp = amp
        if phi is not None:
            self.phi = phi
        if conf is not None:
            self.conf = conf
        if ranks is not None:
            self.ranks = ranks
        if scales is not None:
            self.scales = scales
        if coefficients is not None:
            self.coefficients = coefficients

    def sort(self):
        """
        Return the indices that would sort the data by conf (if available),
        using amp as a tiebreaker. If conf is not available, sorts by amp only.
        Does not modify the instance.

        Returns:
            np.ndarray: Indices for sorting.
        """
        if self.amp is None:
            return None

        if self.conf is not None and len(self.conf) > 0:
            # Sort by conf, then amp
            idx = np.lexsort((self.amp, self.conf))
        else:
            idx = np.argsort(self.amp)

        return idx

    def set(self, field_name, value):
        """
        Set an individual attribute by name.

        Args:
            field_name (str): Name of the attribute to set.
            value (array-like): The value to set (converted to np.array).
        """
        if not hasattr(self, field_name):
            raise AttributeError(f"'AnalysisFigures' object has no attribute '{field_name}'")
        setattr(self, field_name, np.array(value))

    def get(self, field_name):
        """
        Get an individual attribute by name.

        Args:
            field_name (str): Name of the attribute to get.

        Returns:
            np.ndarray: The attribute value.

        Raises:
            AttributeError: If the attribute does not exist.
        """
        if not hasattr(self, field_name):
            raise AttributeError(f"'AnalysisFigures' object has no attribute '{field_name}'")
        return getattr(self, field_name)

    def is_empty(self) -> bool:
        return len(self.figures) == 0

    def __bool__(self):
        return self.is_empty()

    def add_figure(self, fig=None, source: str = ""):
        if fig is not None:
            self.figures.append(fig)
            self.figure_titles.append(source)

    def add_figure_and_show(self, fig:list, source: str = ""):
        self.add_figure(fig,source)

        if "mat" in self.args.engine:
            for i, fig in enumerate(fig):
                fig.show()
            input()
        else:
            conf = {"toImageButtonOptions": {"format": "png", "scale": 4}}
            create_html(fig, self.args.render, conf, source)
            # fig.show(config=conf)


    def __str__(self):
        attrs = ["b", "t", "b_sampled", "t_sampled", "freqs", "amp", "phi", "conf","scales", "coefficients", "ranks"]
        shapes = {attr: getattr(self, attr).shape for attr in attrs}
        return f"AnalysisFigures with data shapes: {shapes}"

    def __add__(self, other):
        """
        Add two AnalysisFigures instances.
        - Appends the list of figures and figure titles.
        - Overwrites all other attributes with those from `other`.

        Args:
            other (AnalysisFigures): Another instance to combine with.

        Returns:
            AnalysisFigures: A new combined instance.
        """
        if not isinstance(other, AnalysisFigures):
            return NotImplemented

        result = AnalysisFigures()

        # Append lists
        result.figures = self.figures + other.figures
        result.figure_titles = self.figure_titles + other.figure_titles

        for attr, value in other.__dict__.items():
            if attr in ["figures", "figure_titles"]:
                continue

            if attr in ["b", "t", "b_sampled", "t_sampled", "freqs", "amp", "phi", "conf","scales", "coefficients"]:
                self_val = getattr(self, attr, None)
                other_val = value
                if self_val is None and other_val is not None:
                    setattr(result, attr, other_val)
                elif self_val is not None and other_val is None:
                    setattr(result, attr, self_val)
                else:
                    # both None or both exist: prefer other
                    setattr(result, attr, other_val)
            else:
                # Overwrite all other attributes from other
                setattr(result, attr, value)

        return result

    def __iadd__(self, other):
        return self.__add__(other)

