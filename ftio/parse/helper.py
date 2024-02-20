import numpy as np

def scale_metric(metric:str,number:float) -> tuple[str, float]:
    """set unit for the plots

    Args:
        number (np.ndarray): array

    Returns:
        unit (string): unit in GB/s, MB/s, KB/s or B/s
        number: scaled array according to the unit
    """
    unit = metric
    order = 1e-0
    prefix = ""
    if number > 0:
        order = np.log10(number)

        if any(x in metric.lower() for x in ["bytes","b", "bandwidth", "transfer"]):
            if order > 9:
                order = 1e-9
                prefix = "G"
            elif order > 6:
                order = 1e-6
                prefix = "M"
            elif order > 3:
                order = 1e-3
                prefix = "K"
            else:
                order = 1e-0
                prefix =""
        elif any(x in metric.lower() for x in ["time","(s)"]):
            if order > 0:
                order = 1e-0
                prefix = ""
            elif order > -3:
                order = 1e-3
                prefix = "μ"
            else:
                order = np.nan
        else:
            return metric, 1e-0

        if not np.isnan(order):
            if any(x in metric.lower() for x in ["(b/s)","(bytes/s)", "(bytes/second)", "(b/second)", "bandwidth"]):
                unit = f"Bandwidth ({prefix}B/s)"
            elif any(x in metric.lower() for x in ["(bytes)","(b)"]):
                unit = f"Size ({prefix}B)"
            elif any(x in metric.lower() for x in ["(s)","(second)", "time"]):
                unit = f"Time ({prefix}s)"
            else:
                unit = "UNKOWN"
        else:
            unit = "UNKOWN"
            order = 1e-0

    return unit, order