from dash_extensions.enrich import DashProxy

from ftio.plot.dash_files.callback_files.io_mode_callbacks import get_io_mode_specific_callbacks
from ftio.plot.dash_files.data_source import get_data_source


def get_callbacks(app: DashProxy, plot_core, io_modes: list[str]) -> None:
    """Is responsible for defining all callbacks for the dash app.

    Args:
        app (DashProxy): The dash app
        plot_core (plot_core): The core component for plotting.
        io_modes (list[str]): All possible io_modes (according to the app).
    """
    for io_mode in io_modes:
        data_source = get_data_source(plot_core, io_mode)
        get_io_mode_specific_callbacks(app, data_source)
