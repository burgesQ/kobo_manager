"""Entry point shim."""

import sys

from modder.cli import main


def run() -> None:
    sys.exit(main())
