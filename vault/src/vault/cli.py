"""vault CLI."""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import shtab

from kobocore.cli import CLIError, add_common_args, check_phase, resolve_device
from kobocore.device import DeviceInfo, pending_updates
from kobocore.log import setup_logging
from kobocore.state import Phase, PipelineState
from vault.exit_codes import (
    NOT_IMPLEMENTED,
    PROCESSING_ERROR,
    SNAPSHOT_NOT_FOUND,
    SUCCESS,
    VERIFY_FAILED,
)
from vault.scope import ScopeOptions, select_files
from vault.snapshot import (
    NICKEL_DB,
    human_size,
    latest_snapshot,
    take_snapshot,
    verify_snapshot,
)
from vault.stats import UnflushedWalError, export_stats

logger = logging.getLogger(__name__)

Handler = Callable[[argparse.Namespace, DeviceInfo, PipelineState], int]


def default_backup_root() -> Path:
    return Path(os.environ.get("KOBO_BACKUP_ROOT") or Path.home() / "kobo-backups")


def _add_backup_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=default_backup_root(),
        help="where snapshots live (default: $KOBO_BACKUP_ROOT or ~/kobo-backups)",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vault",
        description="Snapshot, verify, restore and export reading stats from a Kobo",
    )
    parser.add_argument("--version", action="version", version=version("vault"))
    shtab.add_argument_to(parser, "--print-completion")
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="copy user data + stats off the device")
    add_common_args(snap)
    _add_backup_root(snap)
    snap.add_argument("--with-books", action="store_true", help="also copy books")
    snap.add_argument(
        "--with-koreader",
        action="store_true",
        help="also copy KOReader settings, stats and *.sdr sidecars",
    )

    verify = sub.add_parser("verify", help="re-hash the latest snapshot")
    add_common_args(verify)
    _add_backup_root(verify)
    verify.add_argument("--snapshot", type=Path, help="snapshot dir (default: latest)")

    add_common_args(sub.add_parser("restore", help="not implemented yet"))

    stats = sub.add_parser("export-stats", help="export reading stats to CSV/JSON")
    add_common_args(stats)
    stats.add_argument(
        "--output", type=Path, help="output dir (default: ./kobo-stats-<serial>)"
    )
    return parser


def _snapshot(
    args: argparse.Namespace, device: DeviceInfo, state: PipelineState
) -> int:
    check_phase(state, Phase.BACKED_UP)
    for rel in pending_updates(device.mount):
        logger.warning(
            "pending update staged: %s — Nickel installs it on the next eject "
            "(ROADMAP H5)",
            rel,
        )
    opts = ScopeOptions(with_books=args.with_books, with_koreader=args.with_koreader)
    if args.dry_run:
        rels = select_files(device.mount, opts)
        size = sum((device.mount / rel).stat().st_size for rel in rels)
        logger.info(
            "[dry-run] would copy %d files (%s) into %s/%s/",
            len(rels),
            human_size(size),
            args.backup_root,
            device.serial,
        )
        return SUCCESS
    try:
        result = take_snapshot(
            device, args.hardware.key, args.backup_root, opts, datetime.now(UTC)
        )
    except (OSError, sqlite3.Error, UnflushedWalError) as exc:
        logger.error("snapshot failed: %s", exc)
        raise CLIError(PROCESSING_ERROR) from exc
    logger.info(
        "snapshot %s: %d files, %s (DbVersion %s)",
        result.path,
        len(result.manifest.files),
        human_size(result.manifest.total_size),
        result.manifest.db_version,
    )
    logger.info("next: vault verify")
    state.mark(Phase.BACKED_UP)
    return SUCCESS


def _verify(args: argparse.Namespace, device: DeviceInfo, state: PipelineState) -> int:
    check_phase(state, Phase.VERIFIED)
    snapshot = args.snapshot or latest_snapshot(args.backup_root, device.serial)
    if snapshot is None:
        logger.error("no snapshot for %s under %s", device.serial, args.backup_root)
        raise CLIError(SNAPSHOT_NOT_FOUND)
    result = verify_snapshot(snapshot)
    for path in result.missing:
        logger.error("missing: %s", path)
    for path in result.mismatched:
        logger.error("hash mismatch: %s", path)
    for error in result.sqlite_errors:
        logger.error("integrity_check failed: %s", error)
    if not result.ok:
        raise CLIError(VERIFY_FAILED)
    logger.info("verified %d files in %s", result.checked, snapshot)
    state.mark(Phase.VERIFIED, dry_run=args.dry_run)
    return SUCCESS


def _export_stats(
    args: argparse.Namespace, device: DeviceInfo, state: PipelineState
) -> int:
    out = args.output or Path(f"kobo-stats-{device.serial}")
    if args.dry_run:
        logger.info("[dry-run] would export stats into %s", out)
        return SUCCESS
    try:
        result = export_stats(device.mount / NICKEL_DB, out)
    except (OSError, sqlite3.Error, UnflushedWalError) as exc:
        logger.error("export failed: %s", exc)
        raise CLIError(PROCESSING_ERROR) from exc
    logger.info("exported %d books, %d events to %s", result.books, result.events, out)
    return SUCCESS


def _restore(args: argparse.Namespace, device: DeviceInfo, state: PipelineState) -> int:
    check_phase(state, Phase.RESTORED)
    logger.warning("vault restore: not implemented yet (see ROADMAP.md)")
    return NOT_IMPLEMENTED


_HANDLERS: dict[str, Handler] = {
    "snapshot": _snapshot,
    "verify": _verify,
    "restore": _restore,
    "export-stats": _export_stats,
}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    setup_logging(args)
    try:
        device = resolve_device(args)
        return _HANDLERS[args.command](args, device, PipelineState(device.serial))
    except CLIError as exc:
        return exc.code
