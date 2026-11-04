from pathlib import Path

from vault.cli import main
from vault.exit_codes import (
    DEVICE_NOT_FOUND,
    HARDWARE_MISMATCH,
    PHASE_ERROR,
    SUCCESS,
)


def test_missing_device(tmp_path: Path) -> None:
    assert main(["snapshot"] + ["--mount", str(tmp_path)]) == DEVICE_NOT_FOUND


def test_runs_against_fake_device(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path)
    assert main(["restore", "--mount", str(mount)]) == PHASE_ERROR


def test_hardware_mismatch(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, serial="N999XXXXXXXXX")
    assert main(["snapshot", "--mount", str(mount)]) == HARDWARE_MISMATCH


def test_hardware_alias_accepted(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path)
    rc = main(["snapshot", "--mount", str(mount), "--hardware", "KoLC", "--dry-run"])
    assert rc == SUCCESS
