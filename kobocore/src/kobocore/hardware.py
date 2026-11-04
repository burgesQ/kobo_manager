"""Registry of supported Kobo models, selected on every CLI with ``--hardware``."""

from __future__ import annotations

import re
from typing import NamedTuple


class Hardware(NamedTuple):
    key: str
    name: str
    serial_prefixes: tuple[str, ...]
    device_id: str  # `.kobo/version` field 5, used by Kobo's UpgradeCheck API
    codename: str
    platform: str
    kcc_profile: str  # KindleComicConverter profile (shared with manga_manager)
    colour: bool
    aliases: tuple[str, ...] = ()

    def matches_serial(self, serial: str) -> bool:
        """True if ``serial`` belongs to this model.

        >>> LIBRA_COLOUR.matches_serial("N4284A0218402")
        True
        """
        return serial.startswith(self.serial_prefixes)


LIBRA_COLOUR = Hardware(
    key="libra-colour",
    name="Kobo Libra Colour",
    # Also covers the N428B revision (bigger battery), same platform.
    serial_prefixes=("N428",),
    device_id="00000000-0000-0000-0000-000000000390",
    codename="monza",
    platform="mt8113t-ntx",
    kcc_profile="KoLC",
    colour=True,
    aliases=("libracolor", "kolc"),
)

HARDWARE: dict[str, Hardware] = {hw.key: hw for hw in (LIBRA_COLOUR,)}
DEFAULT_HARDWARE = LIBRA_COLOUR.key


def _norm(name: str) -> str:
    """Case- and separator-insensitive form of a model name.

    >>> _norm("Libra_Colour"), _norm("libra-colour")
    ('libracolour', 'libracolour')
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())


def get_hardware(name: str) -> Hardware:
    """Resolve a key or alias to a registered model.

    >>> get_hardware("LibraColor").key
    'libra-colour'
    """
    wanted = _norm(name)
    for hw in HARDWARE.values():
        if wanted in {_norm(hw.key), *hw.aliases}:
            return hw
    known = ", ".join(sorted(HARDWARE))
    raise ValueError(f"unknown hardware {name!r} (known: {known})")
