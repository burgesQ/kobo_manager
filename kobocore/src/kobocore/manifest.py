"""Backup manifest: what was copied, from which device, with which hashes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import NamedTuple

MANIFEST_NAME = "manifest.json"
MANIFEST_VERSION = 1
_CHUNK = 1 << 20


class FileEntry(NamedTuple):
    path: str  # POSIX path relative to the device root
    size: int
    sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def hash_files(root: Path, rel_paths: list[Path]) -> list[FileEntry]:
    """Hash ``rel_paths`` (relative to ``root``), sorted by path."""
    return [
        FileEntry(rel.as_posix(), (root / rel).stat().st_size, sha256_file(root / rel))
        for rel in sorted(rel_paths)
    ]


@dataclass
class Manifest:
    serial: str
    hardware: str
    firmware: str
    db_version: int | None
    created_at: str
    files: list[FileEntry] = field(default_factory=list)
    # Files copied through the SQLite backup API: `verify` integrity-checks them.
    databases: list[str] = field(default_factory=list)
    version: int = MANIFEST_VERSION

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)

    def write(self, directory: Path) -> Path:
        path = directory / MANIFEST_NAME
        data = asdict(self)
        data["files"] = [f._asdict() for f in self.files]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return path

    @classmethod
    def load(cls, directory: Path) -> Manifest:
        data = json.loads((directory / MANIFEST_NAME).read_text())
        data["files"] = [FileEntry(**f) for f in data["files"]]
        return cls(**data)
