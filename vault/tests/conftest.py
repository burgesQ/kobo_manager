import sqlite3
from pathlib import Path

import pytest

BOOK_ID = "file:///mnt/onboard/Kerr, Philip/La trilogie berlinoise.kepub.epub"


def make_nickel_db(path: Path, db_version: int = 176, wal: bool = True) -> Path:
    """Tiny `KoboReader.sqlite` with the tables and columns vault relies on.

    WAL journal mode by default, like the real Nickel DB.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE DbVersion (version INTEGER);
        CREATE TABLE content (
            ContentID TEXT PRIMARY KEY, ContentType TEXT, Title TEXT,
            Attribution TEXT, Series TEXT, SeriesNumber TEXT, ISBN TEXT,
            ReadStatus INTEGER, ___PercentRead INTEGER, TimeSpentReading INTEGER,
            TimesStartedReading INTEGER, DateLastRead TEXT, DateAdded TEXT,
            LastTimeStartedReading TEXT, LastTimeFinishedReading TEXT
        );
        CREATE TABLE Event (
            EventType INTEGER, FirstOccurrence TEXT, LastOccurrence TEXT,
            EventCount INTEGER, ContentID TEXT, ExtraData BLOB, Checksum TEXT
        );
        """)
    con.execute("INSERT INTO DbVersion VALUES (?)", (db_version,))
    con.executemany(
        "INSERT INTO content (ContentID, ContentType, Title, Attribution, ReadStatus,"
        " ___PercentRead, TimeSpentReading, DateLastRead) VALUES (?,?,?,?,?,?,?,?)",
        [
            (BOOK_ID, "6", "La trilogie berlinoise", "Philip Kerr", 1, 12, 15484,
             "2026-11-04T15:36:05Z"),
            ("unread", "6", "Unread book", "Someone", 0, 0, 0, None),
            (BOOK_ID + "#ch1", "9", "Chapter 1", None, 0, 0, 0, None),
        ],
    )  # fmt: skip
    con.executemany(
        "INSERT INTO Event VALUES (?,?,?,?,?,?,?)",
        [
            (3, "2026-08-01T10:00:00Z", "2026-11-04T15:36:05Z", 12, BOOK_ID, b"\0", ""),
            (46, "2026-08-01T10:00:00Z", "2026-08-01T10:00:00Z", 1, BOOK_ID, None, ""),
        ],
    )  # fmt: skip
    con.commit()
    if wal:
        con.execute("PRAGMA journal_mode=WAL")
    con.close()  # last connection: SQLite checkpoints and removes -wal/-shm
    return path


def populate(mount: Path) -> None:
    """Add the user data, caches and books a real device carries."""
    files = {
        ".kobo/Kobo/Kobo eReader.conf": "[FeatureSettings]\nScreenshots=true\n",
        ".kobo/screensaver/sleep.png": "png",
        ".kobo/dict/dicthtml-fr.zip": "big dictionary",  # re-downloadable
        ".kobo/kepub/store-book": "store book",  # a book
        ".kobo-images/cover.parsed": "cache",
        "fonts/Bookerly.ttf": "font",
        "icons/coffee.png": "icon",
        "Exported Annotations/notes.txt": "note",
        ".adds/nm/qconf": "menu_item:main:Sleep:power:sleep\n",
        ".adds/kfmon/config/kfmon.ini": "[daemon]\n",
        ".adds/nickelclock/settings.ini": "[General]\n",
        ".adds/plato/Settings.toml": "wifi = false\n",
        ".adds/koreader/koreader.sh": "#!/bin/sh\n",
        ".adds/koreader/settings/statistics.sqlite3": "",
        "Kerr, Philip/La trilogie berlinoise.kepub.epub": "epub",
        "Kerr, Philip/La trilogie berlinoise.sdr/metadata.epub.lua": "return {}",
        "screen_001.png": "screenshot",
        "metadata.calibre": "[]",
    }
    for rel, content in files.items():
        path = mount / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    stats = mount / ".adds/koreader/settings/statistics.sqlite3"
    stats.unlink()
    sqlite3.connect(stats).executescript("CREATE TABLE book (id INTEGER);")
    make_nickel_db(mount / ".kobo/KoboReader.sqlite")


@pytest.fixture(autouse=True)
def _isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never touch the real pipeline state or ~/kobo-backups from tests."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("KOBO_BACKUP_ROOT", str(tmp_path / "kobo-backups"))


@pytest.fixture
def nickel_db():
    """Factory fixture: build a tiny Nickel DB at the given path."""
    return make_nickel_db


@pytest.fixture
def make_kobo():
    """Factory fixture: build a fake mounted Kobo tree."""

    def _make(
        root: Path,
        firmware: str = "4.38.23038",
        serial: str = "N428XXXXXXXXX",
        populated: bool = False,
    ) -> Path:
        mount = root / "KOBOeReader"
        (mount / ".kobo").mkdir(parents=True)
        (mount / ".kobo" / "version").write_text(
            f"{serial},4.1.15,{firmware},4.1.15,4.1.15,X\n"
        )
        if populated:
            populate(mount)
        return mount

    return _make
