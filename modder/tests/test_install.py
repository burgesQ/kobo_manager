from pathlib import Path

import pytest

from kobocore.state import Phase, PipelineState
from modder.cli import main
from modder.exit_codes import (
    CLI_ERROR,
    INVALID_PACKAGE,
    PHASE_ERROR,
    SUCCESS,
    UNSAFE_FIRMWARE,
    UPDATE_PENDING,
)
from modder.install import fetch_package


def _install(mount: Path, *extra: str) -> int:
    return main(["install", "nickelmenu", "--mount", str(mount), *extra])


def test_install_needs_restored_phase(tmp_path: Path, make_kobo, nm_package) -> None:
    mount = make_kobo(tmp_path)
    assert _install(mount, "--package", str(nm_package)) == PHASE_ERROR
    assert not (mount / ".kobo/KoboRoot.tgz").exists()


def test_install_stages_koboroot(
    tmp_path: Path, make_kobo, nm_package, restored
) -> None:
    mount = make_kobo(tmp_path)
    assert _install(mount, "--package", str(nm_package)) == SUCCESS
    assert (mount / ".kobo/KoboRoot.tgz").read_bytes() == nm_package.read_bytes()
    assert PipelineState("N428XXXXXXXXX").has(Phase.MODDED)


def test_install_accepts_tar_renamed_download(
    tmp_path: Path, make_kobo, nm_package, restored
) -> None:
    renamed = nm_package.rename(tmp_path / "KoboRoot.tar")  # browser naming trap
    mount = make_kobo(tmp_path)
    assert _install(mount, "--package", str(renamed)) == SUCCESS
    assert (mount / ".kobo/KoboRoot.tgz").is_file()


def test_install_dry_run_stages_nothing(
    tmp_path: Path, make_kobo, nm_package, restored
) -> None:
    mount = make_kobo(tmp_path)
    assert _install(mount, "--package", str(nm_package), "--dry-run") == SUCCESS
    assert not (mount / ".kobo/KoboRoot.tgz").exists()
    assert not PipelineState("N428XXXXXXXXX").has(Phase.MODDED)


def test_install_refuses_pending_update(
    tmp_path: Path, make_kobo, nm_package, restored
) -> None:
    mount = make_kobo(tmp_path, files={".kobo/update.tar": "pending"})
    assert _install(mount, "--package", str(nm_package)) == UPDATE_PENDING


def test_install_rejects_foreign_package(
    tmp_path: Path, make_kobo, bogus_package, restored
) -> None:
    mount = make_kobo(tmp_path)
    assert _install(mount, "--package", str(bogus_package)) == INVALID_PACKAGE
    assert not (mount / ".kobo/KoboRoot.tgz").exists()


def test_install_refuses_unsupported_firmware(
    tmp_path: Path, make_kobo, nm_package, restored
) -> None:
    mount = make_kobo(tmp_path, firmware="6.0.279225")
    assert _install(mount, "--package", str(nm_package)) == UNSAFE_FIRMWARE


def test_install_experimental_needs_opt_in(tmp_path: Path, make_kobo, restored) -> None:
    mount = make_kobo(tmp_path)
    rc = main(["install", "ultimatemangareader", "--mount", str(mount)])
    assert rc == CLI_ERROR


def test_fetch_checks_pinned_sha(tmp_path: Path, nm_package) -> None:
    from kobocore.mods import load_catalogue

    nm = load_catalogue()["nickelmenu"]

    def fake_download(url: str, dest: Path) -> None:
        assert url == nm.download_url
        dest.write_bytes(nm_package.read_bytes())

    with pytest.raises(ValueError, match="sha256"):
        fetch_package(nm, tmp_path / "cache", download=fake_download)
