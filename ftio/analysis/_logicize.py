"""
This file provides functions to logicize time series

Author: Ahmad Tarraf
Copyright (c) 2025 TU Darmstadt, Germany
Date: Mai 26 2025

Licensed under the BSD 3-Clause License.
For more information, see the LICENSE file in the project root:
https://github.com/tuda-parallel/FTIO/blob/main/LICENSE
"""

import numpy as np
from rich.panel import Panel

from ftio.freq.helper import MyConsole


def logicize(b: np.ndarray, verbose: bool = False) -> np.ndarray:

    # b_logic = np.zeros_like(b)
    # for i in range(len(b)):
    #     if b[i] != 0:
    #         b_logic[i] = 1
    #     else:
    #         b_logic[i] = 0
    # vectorize
    b_logic = (b != 0).astype(int)

    text = f"{np.count_nonzero(b_logic)}/{len(b_logic)} non-zero values found"
    console = MyConsole(verbose)
    console.print(
        Panel.fit(
            text[:-1],
            style="white",
            border_style="pink",
            title="Logicalization",
            title_align="left",
        )
    )

    return b_logic
