"""Shared logging setup: ColorFormatter with emoji prefixes."""

from __future__ import annotations

import argparse
import logging
import sys

_PREFIX = {
    logging.DEBUG: "🔍",
    logging.INFO: "📘",
    logging.WARNING: "⚠️ ",
    logging.ERROR: "❌",
    logging.CRITICAL: "💀",
}
_COLOR = {
    logging.DEBUG: "\033[2m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[1;31m",
}
_RESET = "\033[0m"


class ColorFormatter(logging.Formatter):
    def __init__(self, use_color: bool) -> None:
        super().__init__("%(message)s")
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        msg = f"{_PREFIX.get(record.levelno, '')} {super().format(record)}"
        color = _COLOR.get(record.levelno, "")
        return f"{color}{msg}{_RESET}" if self.use_color and color else msg


def add_logging_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--loglevel",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument("--verbose", action="store_true", help="shorthand for DEBUG")


def setup_logging(args: argparse.Namespace) -> None:
    level = logging.DEBUG if args.verbose else getattr(logging, args.loglevel)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorFormatter(sys.stderr.isatty()))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
