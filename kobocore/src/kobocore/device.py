"""Locate a mounted Kobo and read its identity from `.kobo/version`."""

from __future__ import annotations

import getpass
from pathlib import Path
from typing import NamedTuple

from kobocore.firmware import FirmwareVersion, parse_version

VOLUME_LABEL = "KOBOeReader"

# Anything here is installed by Nickel on the next eject/reboot (ROADMAP H5).
PENDING_UPDATE_PATHS = (
    Path(".kobo/KoboRoot.tgz"),
    Path(".kobo/Kobo.tgz"),
    Path(".kobo/update.tar"),
    Path(".kobo/upgrade"),
)


class DeviceInfo(NamedTuple):
    mount: Path
    serial: str
    firmware: FirmwareVersion
    device_id: str = ""

    @property
    def serial_prefix(self) -> str:
        """Model prefix of the serial (e.g. ``N428`` for Libra Colour)."""
        return self.serial[:4]


def candidate_mounts(user: str | None = None) -> list[Path]:
    """Usual Linux automount locations for the Kobo volume.

    >>> [str(p) for p in candidate_mounts("q")]
    ['/media/q/KOBOeReader', '/run/media/q/KOBOeReader']
    """
    user = user or getpass.getuser()
    return [
        Path("/media") / user / VOLUME_LABEL,
        Path("/run/media") / user / VOLUME_LABEL,
    ]


def is_kobo_root(path: Path) -> bool:
    return (path / ".kobo" / "version").is_file()


def find_mount(explicit: Path | None = None) -> Path | None:
    """Return the explicit mount if valid, else the first auto-detected one."""
    if explicit is not None:
        return explicit if is_kobo_root(explicit) else None
    return next((p for p in candidate_mounts() if is_kobo_root(p)), None)


def parse_version_file(content: str) -> tuple[str, FirmwareVersion]:
    """Extract (serial, firmware) from `.kobo/version`.

    The file is a single comma-separated line; field 0 is the serial and
    field 2 the firmware version.

    >>> parse_version_file("N428XXXXXXXXX,4.1.15,4.45.23646,4.1.15,4.1.15,X")
    ('N428XXXXXXXXX', FirmwareVersion(major=4, minor=45, build=23646))
    """
    fields = content.strip().split(",")
    if len(fields) < 3:
        raise ValueError("malformed .kobo/version")
    return fields[0], parse_version(fields[2])


def parse_device_id(content: str) -> str:
    """Field 5 of `.kobo/version`: the id Kobo's update API knows the model by.

    >>> parse_device_id("N428X,4.9.77,4.46.23852,4.9.77,4.9.77,00000000-0390")
    '00000000-0390'
    >>> parse_device_id("N428X,4.1.15,4.38.23038")
    ''
    """
    fields = content.strip().split(",")
    return fields[5] if len(fields) > 5 else ""


def read_device(mount: Path) -> DeviceInfo:
    content = (mount / ".kobo" / "version").read_text()
    serial, fw = parse_version_file(content)
    return DeviceInfo(
        mount=mount, serial=serial, firmware=fw, device_id=parse_device_id(content)
    )


def pending_updates(mount: Path) -> list[Path]:
    """Update packages Nickel will install on the next eject (relative paths)."""
    return [rel for rel in PENDING_UPDATE_PATHS if (mount / rel).exists()]
