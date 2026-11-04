from pathlib import Path

import pytest

from modder.cli import main
from modder.exit_codes import PHASE_ERROR, PROCESSING_ERROR, SUCCESS


def _ssh(mount: Path, *argv: str) -> int:
    return main(["ssh", *argv, "--mount", str(mount)])


def test_status_is_read_only(
    tmp_path: Path, make_kobo, capsys: pytest.CaptureFixture[str]
) -> None:
    mount = make_kobo(tmp_path, files={".kobo/ssh-disabled": "To enable ssh:"})
    assert _ssh(mount, "status") == SUCCESS
    assert "disabled" in capsys.readouterr().err
    assert (mount / ".kobo/ssh-disabled").is_file()


def test_enable_renames_marker(tmp_path: Path, make_kobo, restored) -> None:
    mount = make_kobo(tmp_path, files={".kobo/ssh-disabled": "To enable ssh:"})
    assert _ssh(mount, "enable") == SUCCESS
    assert (mount / ".kobo/ssh-enabled").is_file()
    assert not (mount / ".kobo/ssh-disabled").exists()


def test_disable_renames_marker_back(tmp_path: Path, make_kobo, restored) -> None:
    mount = make_kobo(tmp_path, files={".kobo/ssh-enabled": ""})
    assert _ssh(mount, "disable") == SUCCESS
    assert (mount / ".kobo/ssh-disabled").is_file()


def test_enable_without_server(tmp_path: Path, make_kobo, restored) -> None:
    mount = make_kobo(tmp_path)
    assert _ssh(mount, "enable") == PROCESSING_ERROR


def test_enable_needs_phase(tmp_path: Path, make_kobo) -> None:
    mount = make_kobo(tmp_path, files={".kobo/ssh-disabled": ""})
    assert _ssh(mount, "enable") == PHASE_ERROR


def test_keys_installs_public_keys(tmp_path: Path, make_kobo, restored) -> None:
    pub = tmp_path / "id_ed25519.pub"
    pub.write_text("ssh-ed25519 AAAA me@host\n")
    mount = make_kobo(tmp_path, files={".adds/koreader/koreader.sh": ""})
    assert _ssh(mount, "keys", "--pubkey", str(pub)) == SUCCESS
    for rel in (
        ".adds/koreader/settings/SSH/authorized_keys",
        ".adds/kobo_manager/ssh/authorized_keys",
    ):
        assert (mount / rel).read_text() == "ssh-ed25519 AAAA me@host\n", rel


def test_keys_rejects_private_key(tmp_path: Path, make_kobo, restored) -> None:
    key = tmp_path / "id_ed25519"
    key.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n")
    mount = make_kobo(tmp_path)
    assert _ssh(mount, "keys", "--pubkey", str(key)) == PROCESSING_ERROR
    assert not (mount / ".adds/kobo_manager").exists()
