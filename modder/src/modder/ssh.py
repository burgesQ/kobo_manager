"""SSH on the device (ROADMAP M11).

Two servers exist on this setup:

* the system ``sshd`` started by ``/etc/init.d/ssh`` (KoboStuff/dropbear): it runs at
  boot only when ``.kobo/ssh-enabled`` exists, otherwise it (re)creates
  ``.kobo/ssh-disabled``. ``dropbear -n`` means **no password check** (ROADMAP H7);
  its authorized_keys live on the root filesystem, not reachable over USB, so keys
  are only staged in ``.adds/kobo_manager/ssh/`` (copy step still a spike).
* KOReader's SSH plugin (port 2222, only while KOReader runs), keys in
  ``.adds/koreader/settings/SSH/authorized_keys``.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from modder.ops import Move, Op, WriteText

ENABLED = Path(".kobo/ssh-enabled")
DISABLED = Path(".kobo/ssh-disabled")
STAGED_KEYS = Path(".adds/kobo_manager/ssh/authorized_keys")
KOREADER_KEYS = Path(".adds/koreader/settings/SSH/authorized_keys")
KOREADER_DIR = Path(".adds/koreader")
_PUBKEY_TYPES = ("ssh-", "ecdsa-", "sk-")


class SshState(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    ABSENT = "absent"  # no marker: no init-script SSH server on this firmware


class SshError(Exception):
    pass


def state(mount: Path) -> SshState:
    if (mount / ENABLED).exists():
        return SshState.ENABLED
    if (mount / DISABLED).exists():
        return SshState.DISABLED
    return SshState.ABSENT


def toggle_ops(mount: Path, enable: bool) -> list[Op]:
    current = state(mount)
    if current is SshState.ABSENT:
        raise SshError("no .kobo/ssh-enabled|ssh-disabled marker: no SSH server")
    if (current is SshState.ENABLED) == enable:
        return []
    return [Move(DISABLED, ENABLED) if enable else Move(ENABLED, DISABLED)]


def read_pubkeys(paths: list[Path]) -> str:
    """Concatenate public keys; refuse anything that looks like a private key."""
    lines: list[str] = []
    for path in paths:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "PRIVATE KEY" in line or not line.startswith(_PUBKEY_TYPES):
                raise SshError(f"{path} is not an OpenSSH public key")
            lines.append(line)
    if not lines:
        raise SshError("no public key found (use --pubkey)")
    return "\n".join(lines) + "\n"


def default_pubkeys() -> list[Path]:
    return sorted((Path.home() / ".ssh").glob("*.pub"))


def keys_ops(mount: Path, keys: str) -> list[Op]:
    ops: list[Op] = [WriteText(STAGED_KEYS, keys)]
    if (mount / KOREADER_DIR).is_dir():
        ops.append(WriteText(KOREADER_KEYS, keys))
    return ops
