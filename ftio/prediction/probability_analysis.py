import numpy as np
from rich.console import Console
import ftio.prediction.group as gp
from ftio.prediction.helper import get_dominant
from ftio.prediction.probability import Probability


def find_probability(data: list[dict], method:str = "db") -> list:
    """Calculates the conditional probability that expresses
    how probable the frequency (event A) is given that the signal
    is periodic occurred (probability B).
    According to Bayes' Theorem, P(A|B) = P(B|A)*P(A)/P(B)
    P(B|A): Probability that the signal is periodic given that it has a frequency A --> 1
    P(A): Probability that the signal has the frequency A
    P(B): Probability that the signal has is periodic

    Args:
        data (dict): contacting predictions

    Returns:
        None
    """
    p_b = 0
    p_a = []
    p_a_given_b = 0
    p_b_given_a = 1
    grouped_prediction = []
    counter = 0
    out = []

    if data:
        if "step" in method:
            grouped_prediction, counter = gp.group_step(data)
        elif "db" in method:
            grouped_prediction, counter = gp.group_dbscan(data)

        for prediction in data:
            if len(prediction["dominant_freq"]) >= 1:
                p_b += 1

        p_b = p_b / len(data) 
        CONSOLE = Console()
        CONSOLE.print(f"[purple][PREDICTOR]:[/] P(periodic) = {p_b*100:.3f}%")

        if len(grouped_prediction) > 0:
            for group in range(0, counter + 1):
                p_a = 0
                f_min = np.inf
                f_max = 0
                for pred in grouped_prediction:
                    # print(pred)
                    # print(f"index is {group}, group is {pred['group']}")
                    if group == pred["group"]:
                        f_min = min(get_dominant(pred), f_min)
                        f_max = max(get_dominant(pred), f_max)
                        # print(f"group: {group}, pred_group: {pred['group']}, freq: {get_dominant(pred):.3f}, f_min: {f_min:.3f}, f_max:{f_max:.3f}")
                        p_a += 1

                p_a = p_a / len(data) if len(data) > 0 else 0
                p_a_given_b = p_b_given_a * p_a / p_b if p_b > 0 else 0

                prob = Probability(f_min, f_max)
                prob.set(p_b, p_a, p_a_given_b, p_b_given_a)
                prob.display()
                out.append(prob)

    return out