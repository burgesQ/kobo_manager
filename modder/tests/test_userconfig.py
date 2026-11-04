from pathlib import Path

from modder.userconfig import config_path, dumps_toml, load_config, save_config


def test_dumps_toml_round_trip(tmp_path: Path) -> None:
    data = {
        "nickelmenu": {
            "owner": 'Q "B" — 06',
            "enabled": ["debug.core", "network.ftp"],
            "migrate_legacy": True,
        }
    }
    path = tmp_path / "modder.toml"
    save_config(data, path)
    assert load_config(path) == data
    assert dumps_toml(data).startswith("[nickelmenu]\n")


def test_config_path_follows_xdg(tmp_path: Path) -> None:
    assert config_path() == tmp_path / "config" / "kobo_manager" / "modder.toml"


def test_missing_config_is_empty(tmp_path: Path) -> None:
    assert load_config(tmp_path / "nope.toml") == {}
