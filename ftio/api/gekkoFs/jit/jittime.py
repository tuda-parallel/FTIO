from rich.console import Console
from rich.panel import Panel


class JitTime:
    def __init__(self) -> None:
        self._app = 0
        self._stage_in = 0
        self._stage_out = 0

    @property
    def app(self):
        return self._app

    # setting the apps
    @app.setter
    def app(self, app):
        self._app = app

    # deleting the values
    @app.deleter
    def app(self):
        del self._app

    @property
    def stage_out(self):
        return self._stage_out

    # setting the stage_outs
    @stage_out.setter
    def stage_out(self, stage_out):
        self._stage_out = stage_out

    # deleting the stage_outs
    @stage_out.deleter
    def stage_out(self):
        del self._stage_out

    @property
    def stage_in(self):
        return self._stage_in

    # setting the stage_ins
    @stage_in.setter
    def stage_in(self, stage_in):
        self._stage_in = stage_in

    # deleting the stage_ins
    @stage_in.deleter
    def stage_in(self):
        del self._stage_in

    def print_time(self):
        console = Console()
        text = (
            f"App Time      : {self._app}s\n"
            f"Stage out time: {self._stage_out}s\n"
            f"Stage in time : {self._stage_in}s\n"
            "--------------------------------"
            f"Total time : {self._app + self._stage_out + self._stage_in}s\n"
        )
        console.print(
            Panel.fit(
                "[cyan]" + text,
                title="Total Time",
                style="white",
                border_style="white",
                title_align="left",
            )
        )
