from pathlib import Path

import pytest

from kobocore.firmware import parse_version
from kobocore.mods import Mod, installed_mods, load_catalogue


@pytest.fixture(scope="module")
def catalogue() -> dict[str, Mod]:
    return load_catalogue()


def test_catalogue_has_the_planned_mods(catalogue: dict[str, Mod]) -> None:
    assert {
        "nickelmenu",
        "kfmon",
        "koreader",
        "plato",
        "nickelclock",
        "nickeldbus",
        "rakuyomi",
        "appearance",
        "simpleui",
        "projecttitle",
        "ultimatemangareader",
        "banana",
        "nickelite",
    } <= set(catalogue)


def test_every_entry_is_complete(catalogue: dict[str, Mod]) -> None:
    for key, mod in catalogue.items():
        assert mod.key == key
        assert mod.name and mod.upstream and mod.lines, key
        assert mod.kind in {"nickel-mod", "app", "koreader-plugin", "daemon"}, key


def test_nickelmenu_package_is_pinned(catalogue: dict[str, Mod]) -> None:
    nm = catalogue["nickelmenu"]
    assert nm.version == "0.6.0"
    assert nm.package == "KoboRoot.tgz"
    assert nm.package_marker == "usr/local/Kobo/imageformats/libnm.so"
    assert len(nm.sha256) == 64
    assert nm.download_url == (
        "https://github.com/pgaskin/NickelMenu/releases/download/v0.6.0/KoboRoot.tgz"
    )


def test_firmware_line_support(catalogue: dict[str, Mod]) -> None:
    assert catalogue["nickelmenu"].supports(parse_version("4.46.23852"))
    assert not catalogue["nickelmenu"].supports(parse_version("6.0.279225"))
    assert catalogue["nickelite"].supports(parse_version("6.0.279225"))
    assert catalogue["nickelite"].experimental


def test_koreader_is_kept_by_unmod(catalogue: dict[str, Mod]) -> None:
    assert catalogue["koreader"].keep
    assert catalogue["koreader"].launch.endswith("/.adds/koreader/koreader.sh")


def test_installed_mods_detects_paths(
    tmp_path: Path, catalogue: dict[str, Mod]
) -> None:
    (tmp_path / ".adds/nm").mkdir(parents=True)
    (tmp_path / ".adds/plato").mkdir(parents=True)
    keys = {m.key for m in installed_mods(tmp_path, catalogue)}
    assert keys == {"nickelmenu", "plato"}
