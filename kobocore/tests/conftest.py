from pathlib import Path

import pytest


@pytest.fixture
def fake_kobo(tmp_path: Path) -> Path:
    root = tmp_path / "KOBOeReader"
    (root / ".kobo").mkdir(parents=True)
    (root / ".kobo" / "version").write_text(
        "N428XXXXXXXXX,4.1.15,4.38.23038,4.1.15,4.1.15,X\n"
    )
    return root
