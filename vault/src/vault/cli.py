"""vault CLI."""

from __future__ import annotations

import argparse
import logging
from importlib.metadata import version

import shtab

from kobocore.cli import CLIError, add_common_args, check_phase, resolve_device
from kobocore.log import setup_logging
from kobocore.state import Phase, PipelineState
from vault.exit_codes import NOT_IMPLEMENTED

logger = logging.getLogger(__name__)


_PHASES: dict[str, Phase | None] = {
    "snapshot": Phase.BACKED_UP,
    "verify": Phase.VERIFIED,
    "restore": Phase.RESTORED,
    "export-stats": None,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vault",
        description="Snapshot, verify, restore and export reading stats from a Kobo",
    )
    parser.add_argument("--version", action="version", version=version("vault"))
    shtab.add_argument_to(parser, "--print-completion")
    sub = parser.add_subparsers(dest="command", required=True)
    add_common_args(sub.add_parser("snapshot"))
    add_common_args(sub.add_parser("verify"))
    add_common_args(sub.add_parser("restore"))
    add_common_args(sub.add_parser("export-stats"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    setup_logging(args)
    try:
        device = resolve_device(args)
        phase = _PHASES[args.command]
        if phase is not None:
            check_phase(PipelineState(device.serial), phase)
    except CLIError as exc:
        return exc.code
    logger.warning("vault %s: not implemented yet (see ROADMAP.md)", args.command)
    return NOT_IMPLEMENTED
