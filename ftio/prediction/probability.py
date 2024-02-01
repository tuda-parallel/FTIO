"""Module concerned with probability calculation
"""
from __future__ import annotations
import numpy as np
import ftio.prediction.group as gp
from rich.console import Console
from ftio.prediction.helper import get_dominant

CONSOLE = Console()

def probability(data: list[dict], method:str = "db") -> None:
    """Calculates the conditional probability that expresses
    how probable the frequency (event A) is given that the signal
    is perodic occurred (prabability B).
    According to Bayes' Theorem, P(A|B) = P(B|A)*P(A)/P(B)
    P(B|A): Probability that the signal is perodic given that it has a frequency A --> 1
    P(A): Probability that the signal has the frequency A
    P(B): Probability that the signal has is periodic

    Args:
        data (dict): contating predicitions

    Returns:
        None
    """
    p_b = 0
    p_a = []
    p_a_given_b = 0
    p_b_given_a = 1
    out = []
    counter = 0

    if data:
        if "step" in method:
            out, counter = gp.group_step(data)
        elif "db" in method:
            out, counter = gp.group_dbscan(data)

        for prediction in data:
            if len(prediction["dominant_freq"]) >= 1:
                p_b += 1

        p_b = p_b / len(data) 
        CONSOLE.print(f"[purple][PREDICTOR]:[/] P(periodic) = {p_b*100:.3f}%")

        if len(out) > 0:
            for group in range(0, counter + 1):
                p_a = 0
                f_min = np.inf
                f_max = 0
                for pred in out:
                    # print(pred)
                    # print(f"index is {group}, group is {pred['group']}")
                    if group == pred["group"]:
                        f_min = min(get_dominant(pred), f_min)
                        f_max = max(get_dominant(pred), f_max)
                        # print(f"group: {group}, pred_group: {pred['group']}, freq: {get_dominant(pred):.3f}, f_min: {f_min:.3f}, f_max:{f_max:.3f}")
                        p_a += 1
                p_a = p_a / len(data) if len(data) > 0 else 0
                p_a_given_b = p_b_given_a * p_a / p_b if p_b > 0 else 0
                CONSOLE.print(
                    f"[purple][PREDICTOR]:[/] P([{f_min:.3f},{f_max:.3f}] Hz) = {p_a*100:.2f}%\n"
                    f"[purple][PREDICTOR]:[/] |-> [{f_min:.3f},{f_max:.3f}] Hz = [{1/f_max if f_max != 0 else np.NaN:.3f},{1/f_min if f_min != 0 else np.NaN:.3f}] sec\n"
                    f"[purple][PREDICTOR]:[/] '-> P([{f_min:.3f},{f_max:.3f}] Hz | perodic) = {p_a_given_b*100:.2f}%"
                )
