from __future__ import annotations
from argparse import Namespace
from ftio.freq.freq_html import create_html
from ftio.freq._analysis_figures import AnalysisFigures
from ftio.freq._prediction import Prediction

def convert_and_plot(args: Namespace, list_predictions: list[Prediction],
                     list_analysis_figures: list[AnalysisFigures]) -> None:
    """Convert data from ftio and plot the results.

    Args:
        args (Namespace): Command line arguments.
       list_analysis_figures (list[AnalysisFigures]): List of AnalysisFigures containing the data to plot.
    """

    conf = {"toImageButtonOptions": {"format": "png", "scale": 4}}
    for analysis_figures in list_analysis_figures:
        for i, fig_list in enumerate(analysis_figures.figures):
            if "plotly" in args.engine:
                create_html(fig_list, args.render, conf, analysis_figures.figure_titles[i])


