"""flasher CLI."""

from __future__ import annotations

import argparse
import logging
from importlib.metadata import version
from pathlib import Path

import shtab

from flasher.exit_codes import (
    DEVICE_NOT_FOUND,
    NOT_IMPLEMENTED,
    PHASE_ERROR,
)
from kobocore.device import DeviceInfo, find_mount, read_device
from kobocore.log import add_logging_args, setup_logging
from kobocore.state import Phase, PhaseError, PipelineState

logger = logging.getLogger(__name__)


class _CLIError(Exception):
    """Raised after logging a CLI-level error; carries the exit code."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mount", type=Path, help="Kobo mount point (auto-detected)")
    parser.add_argument(
        "--dry-run", action="store_true", help="log intent, touch nothing"
    )
    add_logging_args(parser)


def _resolve_device(args: argparse.Namespace) -> DeviceInfo:
    mount = find_mount(args.mount)
    if mount is None:
        logger.error("no mounted Kobo found (use --mount)")
        raise _CLIError(DEVICE_NOT_FOUND)
    info = read_device(mount)
    logger.info(
        "device %s on firmware %s at %s", info.serial_prefix, info.firmware, mount
    )
    return info


def _check_phase(state: PipelineState, phase: Phase) -> None:
    try:
        state.require(phase)
    except PhaseError as exc:
        logger.error("%s", exc)
        raise _CLIError(PHASE_ERROR) from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flasher",
        description="Fetch, verify and stage an official Kobo firmware (4.x only)",
    )
    parser.add_argument("--version", action="version", version=version("flasher"))
    shtab.add_argument_to(parser, "--print-completion")
    _add_common_args(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    setup_logging(args)
    try:
        device = _resolve_device(args)
        state = PipelineState(device.serial)
        _check_phase(state, Phase.FLASHED)
    except _CLIError as exc:
        return exc.code
    logger.warning("flasher: not implemented yet (see ROADMAP.md)")
    return NOT_IMPLEMENTED
