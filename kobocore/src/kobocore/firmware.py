"""Firmware version parsing and the 5.x safety guard."""

from __future__ import annotations

from typing import NamedTuple

# NickelMenu / KoboRoot.tgz-based mods only work on the 4.x line.
# Firmware 5.x (Qt6) changes the update mechanism; downgrading from it is
# not reliable. Never flash past this major version without an explicit override.
MAX_SAFE_MAJOR = 4


class FirmwareVersion(NamedTuple):
    major: int
    minor: int
    build: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.build}"

    @property
    def is_mod_safe(self) -> bool:
        """True if NickelMenu-style mods are expected to work.

        >>> parse_version("4.45.23646").is_mod_safe
        True
        >>> parse_version("5.13.241243").is_mod_safe
        False
        """
        return self.major <= MAX_SAFE_MAJOR


def parse_version(raw: str) -> FirmwareVersion:
    """Parse a dotted Kobo firmware version.

    >>> parse_version("4.45.23646")
    FirmwareVersion(major=4, minor=45, build=23646)
    >>> parse_version(" 4.44.23552 ")
    FirmwareVersion(major=4, minor=44, build=23552)
    """
    parts = raw.strip().split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"not a firmware version: {raw!r}")
    major, minor, build = (int(p) for p in parts)
    return FirmwareVersion(major, minor, build)
