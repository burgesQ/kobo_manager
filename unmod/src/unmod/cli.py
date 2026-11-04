"""unmod CLI."""

from __future__ import annotations

import argparse
import logging
from importlib.metadata import version

import shtab

from kobocore.cli import CLIError, add_common_args, check_phase, resolve_device
from kobocore.log import setup_logging
from kobocore.state import Phase, PipelineState
from unmod.exit_codes import NOT_IMPLEMENTED

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="unmod",
        description="Remove NickelMenu, KFMon and patches before a firmware update",
    )
    parser.add_argument("--version", action="version", version=version("unmod"))
    shtab.add_argument_to(parser, "--print-completion")
    add_common_args(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    setup_logging(args)
    try:
        device = resolve_device(args)
        state = PipelineState(device.serial)
        check_phase(state, Phase.UNMODDED)
    except CLIError as exc:
        return exc.code
    logger.warning("unmod: not implemented yet (see ROADMAP.md)")
    return NOT_IMPLEMENTED
