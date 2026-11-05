"""Local user config (``$XDG_CONFIG_HOME/kobo_manager/modder.toml``).

Holds wizard answers and personal data (e.g. the NickelMenu "Device Owner" text) that
must never be committed to the public repository.
"""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Any

Config = dict[str, dict[str, Any]]


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "kobo_manager" / "modder.toml"


def load_config(path: Path) -> Config:
    if not path.is_file():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _value(value: Any) -> str:
    """TOML literal for the few types the config uses.

    >>> _value(True), _value(3), _value('a "b"'), _value(["x", "y"])
    ('true', '3', '"a \\\\"b\\\\""', '["x", "y"]')
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)  # JSON strings are TOML strings
    if isinstance(value, list):
        return "[" + ", ".join(_value(v) for v in value) + "]"
    raise TypeError(f"unsupported config value: {value!r}")


def dumps_toml(config: Config) -> str:
    out: list[str] = []
    for table, values in config.items():
        out.append(f"[{table}]")
        out.extend(f"{key} = {_value(val)}" for key, val in values.items())
        out.append("")
    return "\n".join(out)


def save_config(config: Config, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_toml(config), encoding="utf-8")
