"""Which files of the device a snapshot copies.

Default scope = everything that cannot be re-downloaded or regenerated: the Nickel
database and settings, user fonts/icons/exports, mod configs and screenshots. Books are
opt-in (they live in Calibre), and so is KOReader (installed but unused).
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ALWAYS = (
    ".kobo",
    "fonts",
    "icons",
    "Exported Annotations",
    "Exported Notebooks",
    ".reading-states",
    ".adds/nm",
    ".adds/kfmon/config",
    ".adds/nickelclock/settings.ini",
    ".adds/plato/Settings.toml",
    "metadata.calibre",
    "driveinfo.calibre",
)
ROOT_GLOBS = ("screen_*.png",)
# Bundled with the firmware or re-downloadable: never worth the space.
NEVER = (
    ".kobo/dict",
    ".kobo/iink",
    ".kobo/eLabel",
    ".kobo-images",
    ".thumbnail-previews",
    ".trash",
    ".Trashes",
    "System Volume Information",
)
# Book payloads stored under .kobo by Nickel (store, cloud, audiobooks).
KOBO_BOOKS = (".kobo/kepub", ".kobo/google_drive", ".kobo/dropbox", ".kobo/audiobook")
KOREADER = (
    ".adds/koreader/settings",
    ".adds/koreader/settings.reader.lua",
    ".adds/koreader/history.lua",
)


@dataclass(frozen=True)
class ScopeOptions:
    with_books: bool = False
    with_koreader: bool = False


def _under(rel: PurePosixPath, prefixes: tuple[str, ...]) -> bool:
    """True if ``rel`` is one of ``prefixes`` or inside one of them.

    >>> _under(PurePosixPath(".kobo/dict/fr.zip"), (".kobo/dict",))
    True
    >>> _under(PurePosixPath(".kobo/dictionary"), (".kobo/dict",))
    False
    """
    return any(
        rel == PurePosixPath(p) or PurePosixPath(p) in rel.parents for p in prefixes
    )


def _in_sidecar(rel: PurePosixPath) -> bool:
    """True for files inside a KOReader ``*.sdr`` sidecar directory.

    >>> _in_sidecar(PurePosixPath("A/book.sdr/metadata.epub.lua"))
    True
    """
    return any(part.endswith(".sdr") for part in rel.parts[:-1])


# SQLite side files: transient, and copying them next to a backup-API copy is wrong.
SQLITE_SIDE_SUFFIXES = ("-wal", "-shm", "-journal")


def is_selected(rel: PurePosixPath, opts: ScopeOptions) -> bool:
    if _under(rel, NEVER) or rel.name.endswith(SQLITE_SIDE_SUFFIXES):
        return False
    if _under(rel, KOBO_BOOKS):
        return opts.with_books
    if _under(rel, ALWAYS):
        return True
    if len(rel.parts) == 1 and any(fnmatch.fnmatch(rel.name, g) for g in ROOT_GLOBS):
        return True
    if _under(rel, KOREADER) or _in_sidecar(rel):
        return opts.with_koreader
    if _under(rel, (".adds",)):
        return False  # mod binaries: reinstalled by modder
    return opts.with_books


def select_files(mount: Path, opts: ScopeOptions) -> list[Path]:
    """Relative paths of the regular files to copy, sorted."""
    selected: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(mount):
        here = Path(dirpath).relative_to(mount)
        dirnames[:] = [
            d for d in dirnames if not _under(PurePosixPath(here / d), NEVER)
        ]
        for name in filenames:
            rel = here / name
            if not (mount / rel).is_symlink() and is_selected(PurePosixPath(rel), opts):
                selected.append(rel)
    return sorted(selected)
