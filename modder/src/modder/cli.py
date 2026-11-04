"""modder CLI."""

from __future__ import annotations

import argparse
import logging
from importlib.metadata import version

import shtab

from kobocore.cli import CLIError, add_common_args, check_phase, resolve_device
from kobocore.log import setup_logging
from kobocore.state import Phase, PipelineState
from modder.exit_codes import NOT_IMPLEMENTED

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="modder",
        description="Install KOReader, NickelMenu, screensavers and other mods",
    )
    parser.add_argument("--version", action="version", version=version("modder"))
    shtab.add_argument_to(parser, "--print-completion")
    add_common_args(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    setup_logging(args)
    try:
        device = resolve_device(args)
        state = PipelineState(device.serial)
        check_phase(state, Phase.MODDED)
    except CLIError as exc:
        return exc.code
    logger.warning("modder: not implemented yet (see ROADMAP.md)")
    return NOT_IMPLEMENTED
