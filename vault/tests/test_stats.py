import csv
import json
from pathlib import Path

from vault.stats import export_stats


def test_export_books_and_events(tmp_path: Path, nickel_db) -> None:
    db = nickel_db(tmp_path / "KoboReader.sqlite")
    result = export_stats(db, tmp_path / "out")
    assert (result.books, result.events) == (2, 2)

    with (tmp_path / "out" / "books.csv").open() as fh:
        rows = {r["Title"]: r for r in csv.DictReader(fh)}
    # chapters (ContentType 9) are skipped
    assert set(rows) == {"La trilogie berlinoise", "Unread book"}
    assert rows["La trilogie berlinoise"]["TimeSpentReading"] == "15484"

    events = json.loads((tmp_path / "out" / "events.json").read_text())
    assert {e["EventType"] for e in events} == {3, 46}
    assert all("ExtraData" not in e for e in events)
    assert events[0]["Title"] == "La trilogie berlinoise"


def test_export_tolerates_missing_columns(tmp_path: Path) -> None:
    import sqlite3

    db = tmp_path / "old.sqlite"
    con = sqlite3.connect(db)
    con.executescript("""
        CREATE TABLE content (ContentID TEXT, ContentType TEXT, Title TEXT);
        CREATE TABLE Event (EventType INTEGER, ContentID TEXT);
        INSERT INTO content VALUES ('b', '6', 'Book');
        """)
    con.commit()
    con.close()
    result = export_stats(db, tmp_path / "out")
    assert (result.books, result.events) == (1, 0)
