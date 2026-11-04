"""flasher CLI."""

from __future__ import annotations

import argparse
import logging
from importlib.metadata import version

import shtab

from flasher.exit_codes import NOT_IMPLEMENTED
from kobocore.cli import CLIError, add_common_args, check_phase, resolve_device
from kobocore.log import setup_logging
from kobocore.state import Phase, PipelineState

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flasher",
        description="Fetch, verify and stage an official Kobo firmware (4.x only)",
    )
    parser.add_argument("--version", action="version", version=version("flasher"))
    shtab.add_argument_to(parser, "--print-completion")
    add_common_args(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    setup_logging(args)
    try:
        device = resolve_device(args)
        state = PipelineState(device.serial)
        check_phase(state, Phase.FLASHED)
    except CLIError as exc:
        return exc.code
    logger.warning("flasher: not implemented yet (see ROADMAP.md)")
    return NOT_IMPLEMENTED
