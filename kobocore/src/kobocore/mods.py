"""Mod catalogue loaded from ``data/mods.toml`` (ROADMAP K10)."""

from __future__ import annotations

import tomllib
from importlib.resources import files
from pathlib import Path
from typing import Any, NamedTuple

from kobocore.firmware import FirmwareVersion


class Mod(NamedTuple):
    key: str
    name: str
    kind: str
    lines: tuple[int, ...]
    upstream: str
    detect: tuple[str, ...] = ()
    remove: tuple[str, ...] = ()
    uninstall_create: str = ""
    uninstall_delete: str = ""
    launch: str = ""
    keep: bool = False
    experimental: bool = False
    version: str = ""
    package: str = ""
    package_marker: str = ""
    sha256: str = ""
    notes: str = ""

    def supports(self, firmware: FirmwareVersion) -> bool:
        return firmware.major in self.lines

    def is_installed(self, mount: Path) -> bool:
        return any((mount / rel).exists() for rel in self.detect)

    @property
    def download_url(self) -> str:
        """GitHub release asset URL, or "" when no package is pinned."""
        if not (self.version and self.package and "/" in self.upstream):
            return ""
        return (
            f"https://github.com/{self.upstream}/releases/download/"
            f"v{self.version}/{self.package}"
        )


def _mod(key: str, raw: dict[str, Any]) -> Mod:
    fields: dict[str, Any] = {
        k: tuple(v) if isinstance(v, list) else v for k, v in raw.items()
    }
    return Mod(key=key, **fields)


def load_catalogue() -> dict[str, Mod]:
    data = tomllib.loads(
        files("kobocore").joinpath("data/mods.toml").read_text(encoding="utf-8")
    )
    return {key: _mod(key, raw) for key, raw in data.items()}


def installed_mods(mount: Path, catalogue: dict[str, Mod]) -> list[Mod]:
    return [mod for mod in catalogue.values() if mod.is_installed(mount)]
