import pytest

from kobocore.hardware import DEFAULT_HARDWARE, HARDWARE, get_hardware


def test_default_is_libra_colour() -> None:
    hw = get_hardware(DEFAULT_HARDWARE)
    assert hw.key == "libra-colour"
    assert hw.serial_prefixes == ("N428",)
    assert hw.kcc_profile == "KoLC"


@pytest.mark.parametrize(
    "alias", ["libra-colour", "LibraColour", "LibraColor", "libra_color", "KoLC"]
)
def test_aliases_resolve_to_libra_colour(alias: str) -> None:
    assert get_hardware(alias) is HARDWARE["libra-colour"]


def test_unknown_hardware_lists_known_keys() -> None:
    with pytest.raises(ValueError, match="libra-colour"):
        get_hardware("LibraColor2")


def test_matches_serial_prefix() -> None:
    hw = get_hardware("libra-colour")
    assert hw.matches_serial("N4284A0218402")
    assert not hw.matches_serial("N418XXXXXXXXX")
