from pathlib import Path

import pytest

from vault.cli import main
from vault.exit_codes import (
    DEVICE_NOT_FOUND,
    HARDWARE_MISMATCH,
    NOT_IMPLEMENTED,
    PHASE_ERROR,
)


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


def test_missing_device(tmp_path: Path) -> None:
    assert main(["snapshot"] + ["--mount", str(tmp_path)]) == DEVICE_NOT_FOUND


def test_runs_against_fake_device(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path)
    rc = main(["snapshot"] + ["--mount", str(mount), "--dry-run"])
    assert rc in (NOT_IMPLEMENTED, PHASE_ERROR)


def test_hardware_mismatch(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, serial="N999XXXXXXXXX")
    assert main(["snapshot", "--mount", str(mount)]) == HARDWARE_MISMATCH


def test_hardware_alias_accepted(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path)
    rc = main(["snapshot", "--mount", str(mount), "--hardware", "KoLC"])
    assert rc == NOT_IMPLEMENTED
