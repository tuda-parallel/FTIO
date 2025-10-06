import logging
import importlib.util
import os

COLORLOG_AVAILABLE = importlib.util.find_spec("colorlog") is not None
if COLORLOG_AVAILABLE:
    from colorlog import ColoredFormatter

# ANSI codes fallback if colorlog is unavailable
ANSI_COLORS = {
    "ftio": "\033[36m",  # cyan
    "proxy": "\033[35m",  # purple
    "daemon": "\033[95m",  # pink
    "dlio": "\033[33m",  # yellow
    "lammp": "\033[33m",  # yellow
    "jit": "\033[32m",  # green
    "error": "\033[31m",  # red
    "reset": "\033[0m",
}


class FlushStreamHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)  # emit the log
        self.flush()  # flush immediately


class Logger:
    def __init__(self, level=None, prefix=""):
        self.prefix = (prefix or "GENERAL").lower()  # normalize prefix
        self.logger = logging.getLogger(prefix)
        self.logger.setLevel(self._resolve_level(level))

        # Only add a handler if the logger has no handlers yet
        if not self.logger.handlers:
            handler = FlushStreamHandler()  # subclassed to flush automatically
            handler.setFormatter(self._resolve_formatter())
            self.logger.addHandler(handler)
            self.logger.propagate = False

    def _resolve_level(self, cli_level):
        env_level = os.environ.get("LOG_LEVEL")
        level_name = env_level or cli_level or "DEBUG"
        return getattr(logging, level_name.upper(), logging.INFO)

    def _resolve_formatter(self):
        prefix_upper = self.prefix.upper()
        prefix_color = ANSI_COLORS.get(self.prefix, ANSI_COLORS["reset"])

        if COLORLOG_AVAILABLE:
            # ColoredFormatter with level colors for the message
            base_format = f"[%(asctime)s|{prefix_color}{prefix_upper}{ANSI_COLORS['reset']}|%(levelname)-5s]: %(log_color)s%(message)s%(reset)s"
            return ColoredFormatter(
                fmt=base_format,
                datefmt="%H:%M:%S",
                # datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
                style="%",
            )
        else:
            # Fallback: ANSI codes in message for prefix only
            fmt = f"[%(asctime)s| {prefix_color}{prefix_upper}{ANSI_COLORS['reset']} | %(levelname)-8s]: %(message)s"
            return logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")

    def get(self):
        return self.logger

    def set_prefix(self, new_prefix: str):
        self.prefix = new_prefix.lower()
        # Re-set formatter for all handlers
        for handler in self.logger.handlers:
            handler.setFormatter(self._resolve_formatter())

    def set_level(self, level):
        lvl = self._resolve_level(level)
        self.logger.setLevel(lvl)

    def get_level(self):
        return self.logger.level
