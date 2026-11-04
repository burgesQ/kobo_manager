# kobo_manager

[![CI](https://github.com/burgesQ/kobo_manager/actions/workflows/ci.yml/badge.svg)](https://github.com/burgesQ/kobo_manager/actions/workflows/ci.yml)
[![Docker](https://github.com/burgesQ/kobo_manager/actions/workflows/docker.yml/badge.svg)](https://github.com/burgesQ/kobo_manager/actions/workflows/docker.yml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-2a6db2)](https://mypy-lang.org/)
[![Open in GitHub Codespaces](https://img.shields.io/badge/Codespaces-open-181717?logo=github)](https://codespaces.new/burgesQ/kobo_manager)

A suite of CLI tools to update a modded Kobo e-reader **without losing reading stats** —
backup, un-mod, flash, restore, re-mod.

**Platform:** Linux · **Python:** 3.12+ · **Package manager:** [uv](https://docs.astral.sh/uv/)

---

## Overview

```
mounted Kobo
     │
     ▼
 ┌───────┐  snapshot  ─▶ timestamped backup + sha256 manifest + stats CSV/JSON
 │ vault │  verify    ─▶ hashes + PRAGMA integrity_check
 └───────┘
     │
     ▼
 ┌───────┐
 │ unmod │  ─▶ removes NickelMenu / KFMon / KoboRoot.tgz (keeps KOReader)
 └───────┘
     │
     ▼
 ┌─────────┐
 │ flasher │  ─▶ stages the latest 4.x firmware (refuses 5.x)
 └─────────┘
     │
     ▼
 ┌───────┐
 │ vault │  restore  ─▶ KOReader stats + sidecars, table-level Nickel re-import
 └───────┘
     │
     ▼
 ┌────────┐
 │ modder │  ─▶ KOReader, NickelMenu, screensavers, config
 └────────┘
```

Each step refuses to run until the previous one is recorded as done
(`$XDG_STATE_HOME/kobo_manager/<serial>.json`).

> ⚠️ **Firmware 5.x is not supported** — NickelMenu does not work on it and downgrading
> is unreliable. See `ROADMAP.md` → Known hazards.

## Installation

```bash
git clone https://github.com/burgesQ/kobo_manager.git
cd kobo_manager
uv sync
uv run vault --help
```

### Docker

A prebuilt image (Python 3.12 + uv + all CLIs) is published to GHCR on every push to
`main`:

```bash
docker run --rm -it \
  -v /media/$USER/KOBOeReader:/kobo \
  -v ~/kobo-backups:/root/kobo-backups \
  ghcr.io/burgesq/kobo_manager vault snapshot --mount /kobo --dry-run
```

The same image backs the dev container: open the repo in **GitHub Codespaces** (badge
above) to edit, lint and test from the browser. Device commands obviously need a real
Kobo, so they only make sense locally.

## Status

| Command | State |
|---------|-------|
| `vault snapshot` / `verify` / `export-stats` | ✅ implemented |
| `modder list` / `install` / `wizard nickelmenu` / `ssh` | ✅ implemented, **not yet run on the device** |
| `vault restore`, `unmod`, `flasher` | 🚧 scaffolding (exit `NOT_IMPLEMENTED`, 64) |

See `ROADMAP.md` for the backlog and execution order.

## Backing up

```bash
uv run vault snapshot --dry-run   # what would be copied, and how much
uv run vault snapshot             # ~/kobo-backups/<serial>/<UTC timestamp>/
uv run vault verify               # re-hash + PRAGMA integrity_check, unlocks unmod
uv run vault export-stats --output ./stats
```

A snapshot holds `device/` (copied files, same layout as the device), `stats/`
(`books` and `events` as CSV + JSON) and `manifest.json` (sha256 of every copy).
SQLite databases are copied through the SQLite backup API, read-only.

- Default scope: `.kobo/` (Nickel DB, settings, screensavers), `fonts/`, `icons/`,
  exported annotations/notebooks, `screen_*.png`, NickelMenu/KFMon/NickelClock/Plato
  configs, Calibre device files. Dictionaries, caches and mod binaries are skipped.
- `--with-books`: also copy books. `--with-koreader`: KOReader settings, stats and
  `*.sdr` sidecars.
- `--backup-root` or `$KOBO_BACKUP_ROOT` changes the destination.
- Every CLI takes `--hardware MODEL` (default `libra-colour`).

## Modding

```bash
uv run modder list                                   # catalogue vs installed, per firmware
uv run modder install nickelmenu --dry-run           # pinned v0.6.0, sha256-checked
uv run modder wizard nickelmenu                      # interactive NickelMenu config
uv run modder wizard nickelmenu --non-interactive    # replay saved answers
uv run modder ssh status | enable | disable | keys
```

- The catalogue (`kobocore/src/kobocore/data/mods.toml`) lists every mod with the
  firmware lines it supports, its paths and how it uninstalls.
- `install` stages a `KoboRoot.tgz` (downloaded or `--package`, a browser-renamed
  `.tar` is fine) after checking its content; it refuses when an update is pending.
- The wizard writes one `.adds/nm/kobo_manager_<group>` file per feature group and
  moves old config files to `.adds/kobo_manager/nm-disabled/`. Answers and personal
  data (owner message) live in `~/.config/kobo_manager/modder.toml`, never in the repo.
- Every write needs the pipeline at `restored` and honours `--dry-run`.

## Development

```bash
make test
make lint
make type-check
```
