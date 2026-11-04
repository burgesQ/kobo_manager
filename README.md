# kobo_manager

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
git clone <this repo>
cd kobo_manager
uv sync
uv run vault --help
```

## Status

Scaffolding only: CLIs parse arguments, detect the device and enforce phase order, then
exit with `NOT_IMPLEMENTED` (64). See `ROADMAP.md`.

## Development

```bash
make test
make lint
make type-check
```
