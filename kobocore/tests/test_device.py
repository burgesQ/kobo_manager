from pathlib import Path

from kobocore.device import find_mount, pending_updates, read_device


def test_read_fake_device(fake_kobo: Path) -> None:
    info = read_device(fake_kobo)
    assert info.serial_prefix == "N428"
    assert info.firmware.is_mod_safe


def test_find_mount_rejects_non_kobo(tmp_path: Path) -> None:
    assert find_mount(tmp_path) is None


def test_device_id_is_read_from_field_5(fake_kobo: Path) -> None:
    (fake_kobo / ".kobo" / "version").write_text(
        "N4284A0218402,4.9.77,4.46.23852,4.9.77,4.9.77,"
        "00000000-0000-0000-0000-000000000390"
    )
    assert read_device(fake_kobo).device_id == "00000000-0000-0000-0000-000000000390"


def test_no_pending_updates(fake_kobo: Path) -> None:
    assert pending_updates(fake_kobo) == []


def test_pending_updates_detected(fake_kobo: Path) -> None:
    (fake_kobo / ".kobo" / "KoboRoot.tgz").write_bytes(b"")
    (fake_kobo / ".kobo" / "upgrade").mkdir()
    assert pending_updates(fake_kobo) == [
        Path(".kobo/KoboRoot.tgz"),
        Path(".kobo/upgrade"),
    ]
