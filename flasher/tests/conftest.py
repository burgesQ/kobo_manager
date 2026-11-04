from pathlib import Path

import pytest


@pytest.fixture
def make_kobo():
    """Factory fixture: build a fake mounted Kobo tree."""

    def _make(root: Path, firmware: str = "4.38.23038") -> Path:
        mount = root / "KOBOeReader"
        (mount / ".kobo").mkdir(parents=True)
        (mount / ".kobo" / "version").write_text(
            f"N428XXXXXXXXX,4.1.15,{firmware},4.1.15,4.1.15,X\n"
        )
        return mount

    return _make
