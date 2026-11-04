"""Entry point shim."""

import sys

from flasher.cli import main


def run() -> None:
    sys.exit(main())
