"""Logging utilities."""

import logging
import os

import colorama

_FORMAT = "[%(levelname).1s %(asctime)s %(filename)s:%(lineno)d] %(message)s"
_DATE_FORMAT = "%m-%d %H:%M:%S"


class NewLineFormatter(logging.Formatter):
    """Adds logging prefix to newlines to align multi-line messages."""

    def __init__(self, fmt, datefmt=None, dim=False):
        logging.Formatter.__init__(self, fmt, datefmt)
        self.dim = dim

    def format(self, record):
        msg = logging.Formatter.format(self, record)
        if record.message != "":
            parts = msg.partition(record.message)
            msg = msg.replace("\n", "\r\n" + parts[0])
            if self.dim:
                msg = colorama.Style.DIM + msg + colorama.Style.RESET_ALL
        return msg


FORMATTER = NewLineFormatter(_FORMAT, datefmt=_DATE_FORMAT)


def get_logger(name: str):
    # Determine the logging level based on the KONDUKTOR_DEBUG environment variable
    log_level = logging.INFO
    if os.environ.get("KONDUKTOR_DEBUG", None) == "1":
        log_level = logging.DEBUG

    # Configure the logger
    logger = logging.getLogger(name)
    if not logger.hasHandlers():  # Check if the logger already has handlers
        logger.setLevel(log_level)
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        ch.setFormatter(FORMATTER)
        logger.addHandler(ch)
    logger.propagate = False
    return logger
