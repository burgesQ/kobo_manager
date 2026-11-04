"""Entry point shim."""

import sys

from vault.cli import main


def run() -> None:
    sys.exit(main())
