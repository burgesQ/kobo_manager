"""Pipeline state machine: backup -> verify -> unmod -> flash -> restore -> mod.

Each CLI checks the previous phase is recorded before acting, so a run can
be resumed after an incident and a step can never run out of order.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class Phase(StrEnum):
    BACKED_UP = "backed_up"
    VERIFIED = "verified"
    UNMODDED = "unmodded"
    FLASHED = "flashed"
    RESTORED = "restored"
    MODDED = "modded"


ORDER: list[Phase] = list(Phase)


class PhaseError(Exception):
    """Raised when a phase is attempted before its prerequisite."""


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "kobo_manager"


def prerequisite(phase: Phase) -> Phase | None:
    """Phase that must be done before ``phase``.

    >>> prerequisite(Phase.UNMODDED)
    <Phase.VERIFIED: 'verified'>
    >>> prerequisite(Phase.BACKED_UP) is None
    True
    """
    idx = ORDER.index(phase)
    return ORDER[idx - 1] if idx > 0 else None


class PipelineState:
    def __init__(self, serial: str, root: Path | None = None) -> None:
        self.path = (root or state_dir()) / f"{serial}.json"
        self.done: dict[str, str] = {}
        if self.path.is_file():
            self.done = json.loads(self.path.read_text())

    def has(self, phase: Phase) -> bool:
        return phase.value in self.done

    def require(self, phase: Phase) -> None:
        pre = prerequisite(phase)
        if pre is not None and not self.has(pre):
            raise PhaseError(f"{phase} requires {pre} first")

    def mark(self, phase: Phase, *, dry_run: bool = False) -> None:
        if dry_run:
            return
        self.done[phase.value] = datetime.now(UTC).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.done, indent=2))
