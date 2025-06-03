from ftio.analysis._correlation import (
    extract_correlation_ranges,
    plot_correlation,
    sliding_correlation,
)


def analyze_correlation(
    args,
    prediction,
    coefficients_upsampled,
    t_sampled,
):
    """
    Analyze the correlation between the dominant frequency component (from DFT)
    and the first level of upsampled wavelet coefficients (from DWT).

    Parameters:
        prediction: An object providing DFT-based signal analysis methods.
        coefficients_upsampled: List of upsampled wavelet coefficients at a specific level.
        t_sampled: Time samples corresponding to the signals.
        args: Argument object with attributes like 'freq', 'verbose', and 'engine'.
    """
    if len(prediction.dominant_freq) > 0:
        signal_1 = prediction.get_dominant_wave()
        dominant_name = prediction.get_wave_name(*prediction.get_dominant_freq_amp_phi())
        signal_2 = coefficients_upsampled
        # signal_2 = max(coefficients_upsampled)*logicize(
        # coefficients_upsampled)
        window_duration = 1 / prediction.get_dominant_freq()
        window_size = int(args.freq / prediction.get_dominant_freq())
        corr = sliding_correlation(signal_1, signal_2, window_size)
        # 3) Extract valid ranges and return
        t_corr = t_sampled[: min(len(signal_1), len(signal_2), len(corr))]
        prediction.ranges = extract_correlation_ranges(
            t_corr, corr, min_duration=window_duration, verbose=args.verbose
        )
        if any(x in args.engine for x in ["mat", "plot"]):
            plot_correlation(
                t_sampled,
                signal_1,
                signal_2,
                corr,
                window_duration,
                [
                    f"{dominant_name} (from DFT)",
                    "upsampled approximation coefficients (from DWT)",
                ],
            )
