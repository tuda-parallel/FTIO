"""
Defines the Record type: one measurement value (process count, callpath,
metric, value) collected from FTIO traces and passed to Extra-P for modeling.

Author: Albani Alvarado Mauriello
Copyright (c) 2024-2026 TU Darmstadt, Germany
Date: October 2026

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

from typing import NamedTuple


class Record(NamedTuple):
    """One measurement value for Extra-P"""

    ranks: int  # Coordinate
    callpath: str  # Callpath
    metric: str  # Metric
    value: float  # measurement
