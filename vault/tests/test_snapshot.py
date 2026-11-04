import json
import sqlite3
from pathlib import Path

import pytest

from kobocore.manifest import Manifest, hash_files
from kobocore.state import Phase, PipelineState
from vault.cli import main
from vault.exit_codes import (
    PHASE_ERROR,
    PROCESSING_ERROR,
    SNAPSHOT_NOT_FOUND,
    SUCCESS,
    VERIFY_FAILED,
)

SERIAL = "N428XXXXXXXXX"


def _state() -> PipelineState:
    return PipelineState(SERIAL)


def _snapshot(mount: Path, backups: Path, *extra: str) -> int:
    return main(
        ["snapshot", "--mount", str(mount), "--backup-root", str(backups), *extra]
    )


def _only_snapshot(backups: Path) -> Path:
    [snap] = (backups / SERIAL).iterdir()
    return snap


def test_snapshot_copies_scope_and_writes_manifest(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, firmware="4.46.23852", populated=True)
    assert _snapshot(mount, tmp_path / "bk") == SUCCESS

    snap = _only_snapshot(tmp_path / "bk")
    manifest = Manifest.load(snap)
    assert (manifest.serial, manifest.firmware) == (SERIAL, "4.46.23852")
    assert (manifest.hardware, manifest.db_version) == ("libra-colour", 176)
    paths = {f.path for f in manifest.files}
    assert ".kobo/Kobo/Kobo eReader.conf" in paths
    assert "Kerr, Philip/La trilogie berlinoise.kepub.epub" not in paths
    for entry in manifest.files:
        assert (snap / "device" / entry.path).is_file()
    assert _state().has(Phase.BACKED_UP)


def test_snapshot_sqlite_copy_is_a_valid_database(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    _snapshot(mount, tmp_path / "bk")
    copy = _only_snapshot(tmp_path / "bk") / "device/.kobo/KoboReader.sqlite"
    con = sqlite3.connect(copy)
    assert con.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert con.execute("SELECT count(*) FROM content").fetchone() == (3,)


def test_snapshot_exports_stats(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    _snapshot(mount, tmp_path / "bk")
    stats = _only_snapshot(tmp_path / "bk") / "stats"
    assert len(json.loads((stats / "books.json").read_text())) == 2
    assert (stats / "events.csv").is_file()


def test_snapshot_dry_run_writes_nothing(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    assert _snapshot(mount, tmp_path / "bk", "--dry-run") == SUCCESS
    assert not (tmp_path / "bk").exists()
    assert not _state().has(Phase.BACKED_UP)


def test_snapshot_warns_about_pending_update(
    tmp_path: Path, make_kobo, capsys: pytest.CaptureFixture[str]
) -> None:
    mount = make_kobo(tmp_path, populated=True)
    (mount / ".kobo" / "KoboRoot.tgz").write_bytes(b"pending")
    assert _snapshot(mount, tmp_path / "bk") == SUCCESS
    assert "KoboRoot.tgz" in capsys.readouterr().err


def _verify(mount: Path, backups: Path) -> int:
    return main(["verify", "--mount", str(mount), "--backup-root", str(backups)])


def test_verify_requires_a_snapshot_phase(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    assert _verify(mount, tmp_path / "bk") == PHASE_ERROR


def test_verify_marks_verified(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    _snapshot(mount, tmp_path / "bk")
    assert _verify(mount, tmp_path / "bk") == SUCCESS
    assert _state().has(Phase.VERIFIED)


def test_verify_detects_tampering(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    _snapshot(mount, tmp_path / "bk")
    conf = _only_snapshot(tmp_path / "bk") / "device/.kobo/Kobo/Kobo eReader.conf"
    conf.write_text("tampered")
    assert _verify(mount, tmp_path / "bk") == VERIFY_FAILED
    assert not _state().has(Phase.VERIFIED)


def test_verify_detects_corrupt_sqlite(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    _snapshot(mount, tmp_path / "bk")
    snap = _only_snapshot(tmp_path / "bk")
    db = snap / "device/.kobo/KoboReader.sqlite"
    db.write_bytes(b"not a database" * 100)
    manifest = Manifest.load(snap)  # re-hash so only the SQLite check can fail
    manifest.files = hash_files(snap / "device", [Path(f.path) for f in manifest.files])
    manifest.write(snap)
    assert _verify(mount, tmp_path / "bk") == VERIFY_FAILED


def test_verify_without_snapshot_dir(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    _state().mark(Phase.BACKED_UP)
    assert _verify(mount, tmp_path / "bk") == SNAPSHOT_NOT_FOUND


def test_export_stats_to_output_dir(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    out = tmp_path / "out"
    rc = main(["export-stats", "--mount", str(mount), "--output", str(out)])
    assert rc == SUCCESS
    assert (out / "books.csv").is_file()


def _side_files(root: Path) -> list[str]:
    suffixes = ("-wal", "-shm", "-journal")
    return sorted(str(p) for p in root.rglob("*") if p.name.endswith(suffixes))


def test_wal_database_leaves_no_side_files(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)  # WAL-mode DB, like a real Kobo
    backups = tmp_path / "bk"
    assert _snapshot(mount, backups) == SUCCESS
    assert _verify(mount, backups) == SUCCESS
    out = tmp_path / "out"
    assert main(["export-stats", "--mount", str(mount), "--output", str(out)]) == 0
    assert _side_files(mount) == []
    assert _side_files(backups) == []


def test_snapshot_copy_uses_rollback_journal(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    _snapshot(mount, tmp_path / "bk")
    copy = _only_snapshot(tmp_path / "bk") / "device/.kobo/KoboReader.sqlite"
    assert copy.read_bytes()[18:20] == b"\x01\x01"  # 2,2 would mean WAL


def test_snapshot_refuses_unflushed_wal(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, populated=True)
    (mount / ".kobo/KoboReader.sqlite-wal").write_bytes(b"uncheckpointed" * 64)
    assert _snapshot(mount, tmp_path / "bk") == PROCESSING_ERROR
    assert not (tmp_path / "bk" / SERIAL).exists() or not any(
        (tmp_path / "bk" / SERIAL).iterdir()
    )
