"""Export Nickel's native reading stats to CSV and JSON (ROADMAP S1).

Columns are intersected with the live schema so an older or newer `KoboReader.sqlite`
still exports whatever it has.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any, NamedTuple

BOOK_COLUMNS = (
    "ContentID",
    "Title",
    "Attribution",
    "Series",
    "SeriesNumber",
    "ISBN",
    "ReadStatus",
    "___PercentRead",
    "TimeSpentReading",
    "TimesStartedReading",
    "FirstTimeReading",
    "DateLastRead",
    "LastTimeStartedReading",
    "LastTimeFinishedReading",
    "DateAdded",
)
EVENT_COLUMNS = (
    "EventType",
    "FirstOccurrence",
    "LastOccurrence",
    "EventCount",
    "ContentID",
)
BOOK_CONTENT_TYPE = 6  # 9 = chapters / parts of a book


class StatsResult(NamedTuple):
    books: int
    events: int


class UnflushedWalError(RuntimeError):
    """The database has uncheckpointed changes in its ``-wal`` file."""


def open_readonly(db: Path) -> sqlite3.Connection:
    """Open ``db`` without creating or touching any file next to it.

    Nickel keeps `KoboReader.sqlite` in WAL mode: even a ``mode=ro`` connection would
    create ``-wal``/``-shm`` files on the device. ``immutable=1`` never does, but it
    ignores the ``-wal`` file, so a non-empty one (changes not yet merged) is refused.
    """
    wal = db.with_name(db.name + "-wal")
    if wal.is_file() and wal.stat().st_size > 0:
        raise UnflushedWalError(
            f"{wal} holds changes not merged into the database yet: "
            "let Nickel close it (eject, wait for the home screen, reconnect)"
        )
    con = sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro&immutable=1", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _columns(con: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in con.execute(f'PRAGMA table_info("{table}")')}


def _select(wanted: tuple[str, ...], present: set[str], alias: str) -> list[str]:
    return [f'{alias}."{c}"' for c in wanted if c in present]


def _book_rows(con: sqlite3.Connection) -> list[dict[str, Any]]:
    present = _columns(con, "content")
    cols = _select(BOOK_COLUMNS, present, "c")
    if not cols or "ContentType" not in present:
        return []
    order = ' ORDER BY c."DateLastRead" DESC' if "DateLastRead" in present else ""
    sql = (
        f"SELECT {', '.join(cols)} FROM content c"
        f' WHERE CAST(c."ContentType" AS INTEGER) = {BOOK_CONTENT_TYPE}{order}'
    )
    return [dict(r) for r in con.execute(sql)]


def _event_rows(con: sqlite3.Connection) -> list[dict[str, Any]]:
    present = _columns(con, "Event")
    cols = _select(EVENT_COLUMNS, present, "e")
    if not cols:
        return []
    title = ""
    join = ""
    if "ContentID" in present and "Title" in _columns(con, "content"):
        title = ', c."Title" AS Title'
        join = ' LEFT JOIN content c ON c."ContentID" = e."ContentID"'
    order = ' ORDER BY e."LastOccurrence" DESC' if "LastOccurrence" in present else ""
    sql = f"SELECT {', '.join(cols)}{title} FROM Event e{join}{order}"
    return [dict(r) for r in con.execute(sql)]


def _write(rows: list[dict[str, Any]], out_dir: Path, stem: str) -> None:
    (out_dir / f"{stem}.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    )
    with (out_dir / f"{stem}.csv").open("w", newline="") as fh:
        if rows:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def export_stats(db: Path, out_dir: Path) -> StatsResult:
    """Write ``books.{csv,json}`` and ``events.{csv,json}`` into ``out_dir``."""
    con = open_readonly(db)
    try:
        books, events = _book_rows(con), _event_rows(con)
    finally:
        con.close()
    out_dir.mkdir(parents=True, exist_ok=True)
    _write(books, out_dir, "books")
    _write(events, out_dir, "events")
    return StatsResult(len(books), len(events))
