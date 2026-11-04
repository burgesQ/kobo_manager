"""Take and verify snapshots (ROADMAP V1–V6, S3).

Layout::

    <backup-root>/<serial>/<UTC timestamp>/
        manifest.json   # kobocore.manifest.Manifest, hashes of the *copies*
        device/         # selected files, same relative paths as on the device
        stats/          # books/events CSV+JSON exported from the copied DB

A snapshot is written to ``<timestamp>.partial`` and renamed when complete, so an
interrupted run is never mistaken for a backup.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from kobocore.device import DeviceInfo
from kobocore.manifest import MANIFEST_NAME, Manifest, hash_files, sha256_file
from vault.scope import ScopeOptions, select_files
from vault.stats import export_stats, open_readonly

logger = logging.getLogger(__name__)

SQLITE_SUFFIXES = (".sqlite", ".sqlite3")
NICKEL_DB = Path(".kobo/KoboReader.sqlite")
PARTIAL = ".partial"


class SnapshotResult(NamedTuple):
    path: Path
    manifest: Manifest


class VerifyResult(NamedTuple):
    checked: int
    missing: list[str]
    mismatched: list[str]
    sqlite_errors: list[str]

    @property
    def ok(self) -> bool:
        return not (self.missing or self.mismatched or self.sqlite_errors)


def snapshot_name(now: datetime) -> str:
    """Directory name for a snapshot taken at ``now`` (FAT/Windows safe).

    >>> from datetime import UTC
    >>> snapshot_name(datetime(2026, 11, 4, 17, 30, 5, tzinfo=UTC))
    '2026-11-04T17-30-05Z'
    """
    return now.strftime("%Y-%m-%dT%H-%M-%SZ")


def human_size(size: int) -> str:
    """
    >>> human_size(512), human_size(61_865_984)
    ('512 B', '59.0 MiB')
    """
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def is_sqlite(path: Path) -> bool:
    return path.suffix in SQLITE_SUFFIXES


def _copy_sqlite(src: Path, dst: Path) -> None:
    """Consistent copy through the SQLite backup API (ROADMAP V2)."""
    source = open_readonly(src)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def copy_file(src: Path, dst: Path) -> bool:
    """Copy ``src`` to ``dst``; True if it went through the SQLite backup API."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if is_sqlite(src):
        try:
            _copy_sqlite(src, dst)
            return True
        except sqlite3.DatabaseError as exc:
            logger.warning("%s is not a readable database (%s): raw copy", src, exc)
            dst.unlink(missing_ok=True)
    shutil.copy2(src, dst)
    return False


def read_db_version(db: Path) -> int | None:
    if not db.is_file():
        return None
    con = open_readonly(db)
    try:
        row = con.execute("SELECT version FROM DbVersion").fetchone()
    except sqlite3.DatabaseError:
        return None
    finally:
        con.close()
    return int(row[0]) if row else None


def take_snapshot(
    device: DeviceInfo,
    hardware: str,
    backup_root: Path,
    opts: ScopeOptions,
    now: datetime,
) -> SnapshotResult:
    rels = select_files(device.mount, opts)
    final = backup_root / device.serial / snapshot_name(now)
    work = final.with_name(final.name + PARTIAL)
    files_dir = work / "device"
    files_dir.mkdir(parents=True)
    databases: list[str] = []
    for rel in rels:
        logger.debug("copy %s", rel)
        if copy_file(device.mount / rel, files_dir / rel):
            databases.append(rel.as_posix())

    manifest = Manifest(
        serial=device.serial,
        hardware=hardware,
        firmware=str(device.firmware),
        db_version=read_db_version(files_dir / NICKEL_DB),
        created_at=now.isoformat(),
        files=hash_files(files_dir, rels),
        databases=databases,
    )
    manifest.write(work)
    if (files_dir / NICKEL_DB).is_file():
        stats = export_stats(files_dir / NICKEL_DB, work / "stats")
        logger.info("exported stats: %d books, %d events", stats.books, stats.events)
    work.rename(final)
    return SnapshotResult(final, manifest)


def latest_snapshot(backup_root: Path, serial: str) -> Path | None:
    base = backup_root / serial
    if not base.is_dir():
        return None
    complete = [
        d
        for d in base.iterdir()
        if d.is_dir() and not d.name.endswith(PARTIAL) and (d / MANIFEST_NAME).is_file()
    ]
    return max(complete, default=None)


def _integrity_error(db: Path) -> str | None:
    try:
        con = open_readonly(db)
        try:
            result = con.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            con.close()
    except sqlite3.DatabaseError as exc:
        return str(exc)
    return None if result == "ok" else str(result)


def verify_snapshot(snapshot: Path) -> VerifyResult:
    manifest = Manifest.load(snapshot)
    databases = set(manifest.databases)
    files_dir = snapshot / "device"
    missing: list[str] = []
    mismatched: list[str] = []
    sqlite_errors: list[str] = []
    for entry in manifest.files:
        path = files_dir / entry.path
        if not path.is_file():
            missing.append(entry.path)
            continue
        if path.stat().st_size != entry.size or sha256_file(path) != entry.sha256:
            mismatched.append(entry.path)
            continue
        if entry.path in databases and (error := _integrity_error(path)):
            sqlite_errors.append(f"{entry.path}: {error}")
    return VerifyResult(len(manifest.files), missing, mismatched, sqlite_errors)
