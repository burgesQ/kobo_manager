"""Entry point shim."""

import sys

from unmod.cli import main


def run() -> None:
    sys.exit(main())
