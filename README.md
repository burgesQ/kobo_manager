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

Scaffolding only: CLIs parse arguments, detect the device and enforce phase order, then
exit with `NOT_IMPLEMENTED` (64). See `ROADMAP.md`.

## Development

```bash
make test
make lint
make type-check
```
