"""Device writes as data: build a list of ops, log it, then apply it (or not).

Every modder write goes through :func:`apply`, so ``--dry-run`` is one flag.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)


class WriteText(NamedTuple):
    rel: Path
    content: str


class Move(NamedTuple):
    src: Path  # relative to the mount
    dst: Path


class CopyIn(NamedTuple):
    local: Path  # absolute path on this computer
    rel: Path


Op = WriteText | Move | CopyIn


def describe(op: Op) -> str:
    """
    >>> describe(WriteText(Path(".adds/nm/x"), "abc"))
    'write .adds/nm/x (3 bytes)'
    """
    match op:
        case WriteText(rel, content):
            return f"write {rel} ({len(content.encode())} bytes)"
        case Move(src, dst):
            return f"move {src} -> {dst}"
        case CopyIn(local, rel):
            return f"copy {local} -> {rel}"
    raise TypeError(op)


def apply(mount: Path, ops: list[Op], *, dry_run: bool) -> None:
    for op in ops:
        logger.info("%s%s", "[dry-run] " if dry_run else "", describe(op))
        if dry_run:
            continue
        match op:
            case WriteText(rel, content):
                (mount / rel).parent.mkdir(parents=True, exist_ok=True)
                (mount / rel).write_text(content)
            case Move(src, dst):
                (mount / dst).parent.mkdir(parents=True, exist_ok=True)
                (mount / src).replace(mount / dst)
            case CopyIn(local, rel):
                (mount / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(local, mount / rel)
