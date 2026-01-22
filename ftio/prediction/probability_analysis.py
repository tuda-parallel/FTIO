import numpy as np
from rich.console import Console

import ftio.prediction.group as gp
from ftio.prediction.helper import get_dominant
from ftio.prediction.probability import Probability
from ftio.prediction.change_point_detection import ChangePointDetector


def find_probability(data: list[dict], method: str = "db", counter: int = -1) -> list:
    """Calculates the conditional probability that expresses
    how probable the frequency (event A) is given that the signal
    is periodic occurred (probability B).
    According to Bayes' Theorem, P(A|B) = P(B|A)*P(A)/P(B)
    P(B|A): Probability that the signal is periodic given that it has a frequency A --> 1
    P(A): Probability that the signal has the frequency A
    P(B): Probability that the signal has is periodic

    Args:
        data (dict): contacting predictions
        method (str): method to group the predictions (step or db)
        counter (int): number of predictions already executed

    Returns:
        out (dict): probability of predictions in ranges
    """
    p_b = 0
    p_a = []
    p_a_given_b = 0
    p_b_given_a = 1
    grouped_prediction = []
    number_groups = 0
    out = []

    if counter > 0:
        prefix = f"[purple][PREDICTOR] (#{counter}):[/]"
    else:
        prefix = "[purple][PREDICTOR][/]"

    if data:
        if "step" in method:
            grouped_prediction, number_groups = gp.group_step(data)
        elif "db" in method:
            grouped_prediction, number_groups = gp.group_dbscan(data)

        for prediction in data:
            if len(prediction["dominant_freq"]) >= 1:
                p_b += 1

        p_b = p_b / len(data)
        console = Console()
        console.print(f"{prefix} P(periodic) = {p_b*100:.3f}%")

        if len(grouped_prediction) > 0:
            for group in range(0, number_groups + 1):
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
                prob.display(prefix)
                out.append(prob)

    return out


def detect_pattern_change(shared_resources, prediction, detector, count):
    """Detect pattern changes in predictions.

    Args:
        shared_resources: Shared resources for multiprocessing
        prediction: Current prediction object
        detector: Change point detector instance
        count: Prediction counter

    Returns:
        tuple: (change_detected, change_log, start_time)
    """
    if prediction is None or detector is None:
        return False, "", 0.0

    freq = get_dominant(prediction)

    if freq is None or np.isnan(freq):
        return False, "", getattr(prediction, 't_start', 0.0)

    current_time = getattr(prediction, 't_end', 0.0)

    if hasattr(detector, 'verbose') and detector.verbose:
        console = Console()
        console.print(f"[cyan][DEBUG] Change point detection called for prediction #{count}, freq={freq:.3f} Hz[/]")
        frequencies = getattr(detector, 'frequencies', [])
        is_calibrated = getattr(detector, 'is_calibrated', False)
        console.print(f"[cyan][DEBUG] Detector calibrated: {is_calibrated}, samples: {len(frequencies)}[/]")

    result = detector.add_prediction(prediction, current_time)

    if hasattr(detector, 'verbose') and detector.verbose:
        console = Console()
        console.print(f"[cyan][DEBUG] Detector result: {result}[/]")

    if result is not None:
        change_point_idx, change_point_time = result

        if hasattr(detector, 'verbose') and detector.verbose:
            console = Console()
            console.print(f"[green][DEBUG] CHANGE POINT DETECTED! Index: {change_point_idx}, Time: {change_point_time:.3f}[/]")

        change_log = f"[red bold][CHANGE_POINT] t_s={change_point_time:.3f} sec[/]"
        change_log += f"\n[purple][PREDICTOR] (#{count}):[/][yellow] Adapting analysis window to start at t_s={change_point_time:.3f}[/]"

        return True, change_log, change_point_time

    return False, "", getattr(prediction, 't_start', 0.0)
