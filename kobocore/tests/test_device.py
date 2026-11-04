from pathlib import Path

from kobocore.device import find_mount, read_device


def test_read_fake_device(fake_kobo: Path) -> None:
    info = read_device(fake_kobo)
    assert info.serial_prefix == "N428"
    assert info.firmware.is_mod_safe


def test_find_mount_rejects_non_kobo(tmp_path: Path) -> None:
    assert find_mount(tmp_path) is None
