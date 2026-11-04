"""Argument parsing and device resolution shared by every CLI.

Helpers log the problem, then raise :class:`CLIError` carrying the exit code, so each
``main()`` stays a flat orchestrator::

    try:
        device = resolve_device(args)
        check_phase(PipelineState(device.serial), Phase.UNMODDED)
    except CLIError as exc:
        return exc.code
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from kobocore.device import DeviceInfo, find_mount, read_device
from kobocore.exit_codes import DEVICE_NOT_FOUND, HARDWARE_MISMATCH, PHASE_ERROR
from kobocore.hardware import DEFAULT_HARDWARE, HARDWARE, Hardware, get_hardware
from kobocore.log import add_logging_args
from kobocore.state import Phase, PhaseError, PipelineState

logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Raised after logging a CLI-level error; carries the exit code."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def _hardware_arg(value: str) -> Hardware:
    try:
        return get_hardware(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add ``--mount``, ``--dry-run``, ``--hardware`` and the logging flags."""
    parser.add_argument("--mount", type=Path, help="Kobo mount point (auto-detected)")
    parser.add_argument(
        "--dry-run", action="store_true", help="log intent, touch nothing"
    )
    parser.add_argument(
        "--hardware",
        type=_hardware_arg,
        default=DEFAULT_HARDWARE,  # argparse runs `type` on str defaults
        metavar="MODEL",
        help=f"target model: {', '.join(sorted(HARDWARE))} (default: %(default)s)",
    )
    add_logging_args(parser)


def resolve_device(args: argparse.Namespace) -> DeviceInfo:
    """Find the mounted Kobo and check it is the selected ``--hardware``."""
    mount = find_mount(args.mount)
    if mount is None:
        logger.error("no mounted Kobo found (use --mount)")
        raise CLIError(DEVICE_NOT_FOUND)
    info = read_device(mount)
    hardware: Hardware = args.hardware
    if not hardware.matches_serial(info.serial):
        logger.error(
            "device %s is not a %s (expected serial prefix %s); pass --hardware",
            info.serial_prefix,
            hardware.name,
            "/".join(hardware.serial_prefixes),
        )
        raise CLIError(HARDWARE_MISMATCH)
    logger.info(
        "%s (%s) on firmware %s at %s",
        hardware.name,
        info.serial_prefix,
        info.firmware,
        mount,
    )
    return info


def check_phase(state: PipelineState, phase: Phase) -> None:
    """Refuse to run ``phase`` before its prerequisite is recorded."""
    try:
        state.require(phase)
    except PhaseError as exc:
        logger.error("%s", exc)
        raise CLIError(PHASE_ERROR) from exc
