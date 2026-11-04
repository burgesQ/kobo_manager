import argparse
from pathlib import Path

import pytest

from kobocore.cli import CLIError, add_common_args, check_phase, resolve_device
from kobocore.exit_codes import DEVICE_NOT_FOUND, HARDWARE_MISMATCH, PHASE_ERROR
from kobocore.hardware import HARDWARE
from kobocore.state import Phase, PipelineState


def _parse(*argv: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_common_args(parser)
    return parser.parse_args(list(argv))


def _write_version(mount: Path, serial: str) -> Path:
    (mount / ".kobo").mkdir(parents=True)
    (mount / ".kobo" / "version").write_text(
        f"{serial},4.9.77,4.46.23852,4.9.77,4.9.77,X\n"
    )
    return mount


def test_hardware_defaults_to_libra_colour() -> None:
    assert _parse().hardware is HARDWARE["libra-colour"]


def test_hardware_alias_is_normalised() -> None:
    assert _parse("--hardware", "LibraColor").hardware is HARDWARE["libra-colour"]


def test_unknown_hardware_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        _parse("--hardware", "LibraColor2")
    assert exc.value.code == 2
    assert "libra-colour" in capsys.readouterr().err


def test_common_args_present() -> None:
    args = _parse("--mount", "/x", "--dry-run", "--verbose")
    assert args.mount == Path("/x")
    assert args.dry_run and args.verbose


def test_resolve_device_missing(tmp_path: Path) -> None:
    with pytest.raises(CLIError) as exc:
        resolve_device(_parse("--mount", str(tmp_path)))
    assert exc.value.code == DEVICE_NOT_FOUND


def test_resolve_device_ok(tmp_path: Path) -> None:
    mount = _write_version(tmp_path / "K", "N4284A0218402")
    info = resolve_device(_parse("--mount", str(mount)))
    assert info.serial_prefix == "N428"


def test_resolve_device_hardware_mismatch(tmp_path: Path) -> None:
    mount = _write_version(tmp_path / "K", "N418XXXXXXXXX")
    with pytest.raises(CLIError) as exc:
        resolve_device(_parse("--mount", str(mount)))
    assert exc.value.code == HARDWARE_MISMATCH


def test_check_phase_out_of_order(tmp_path: Path) -> None:
    with pytest.raises(CLIError) as exc:
        check_phase(PipelineState("N428TEST", root=tmp_path), Phase.FLASHED)
    assert exc.value.code == PHASE_ERROR
