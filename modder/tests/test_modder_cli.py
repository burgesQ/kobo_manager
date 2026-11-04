from pathlib import Path

import pytest

from modder.cli import main
from modder.exit_codes import DEVICE_NOT_FOUND, HARDWARE_MISMATCH, SUCCESS


def test_missing_device(tmp_path: Path) -> None:
    assert main(["list", "--mount", str(tmp_path)]) == DEVICE_NOT_FOUND


def test_hardware_mismatch(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, serial="N999XXXXXXXXX")
    assert (
        main(["list", "--mount", str(mount), "--hardware", "libra-colour"])
        == HARDWARE_MISMATCH
    )


def test_list_is_read_only_and_needs_no_phase(
    tmp_path: Path, make_kobo, capsys: pytest.CaptureFixture[str]
) -> None:
    mount = make_kobo(tmp_path, files={".adds/nm/qconf": "", ".adds/plato/x": ""})
    before = sorted(p for p in mount.rglob("*"))
    assert main(["list", "--mount", str(mount)]) == SUCCESS
    assert sorted(p for p in mount.rglob("*")) == before
    err = capsys.readouterr().err
    assert "nickelmenu" in err and "installed" in err
