import io
import tarfile
from pathlib import Path

import pytest

from kobocore.state import Phase, PipelineState

SERIAL = "N428XXXXXXXXX"


@pytest.fixture(autouse=True)
def _isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never touch the real pipeline state, user config or cache from tests."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))


@pytest.fixture
def make_kobo():
    """Factory fixture: build a fake mounted Kobo tree."""

    def _make(
        root: Path,
        firmware: str = "4.46.23852",
        serial: str = SERIAL,
        files: dict[str, str] | None = None,
    ) -> Path:
        mount = root / "KOBOeReader"
        (mount / ".kobo").mkdir(parents=True)
        (mount / ".kobo" / "version").write_text(
            f"{serial},4.1.15,{firmware},4.1.15,4.1.15,X\n"
        )
        for rel, content in (files or {}).items():
            path = mount / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return mount

    return _make


@pytest.fixture
def restored() -> None:
    """Record every phase up to RESTORED so modder may write."""
    state = PipelineState(SERIAL)
    for phase in (
        Phase.BACKED_UP,
        Phase.VERIFIED,
        Phase.UNMODDED,
        Phase.FLASHED,
        Phase.RESTORED,
    ):
        state.mark(phase)


def make_package(path: Path, members: dict[str, bytes]) -> Path:
    """Build a KoboRoot.tgz-style archive (member names prefixed with ./)."""
    with tarfile.open(path, "w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(f"./{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


@pytest.fixture
def nm_package(tmp_path: Path) -> Path:
    return make_package(
        tmp_path / "KoboRoot.tgz",
        {
            "usr/local/Kobo/imageformats/libnm.so": b"\x7fELF",
            "mnt/onboard/.adds/nm/doc": b"# NickelMenu",
        },
    )


@pytest.fixture
def bogus_package(tmp_path: Path) -> Path:
    return make_package(tmp_path / "other.tgz", {"usr/bin/evil": b"x"})
