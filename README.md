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
 │ flasher │  ─▶ stages the latest 4.x firmware (refuses 5.x/6.x; `watch` monitors them)
 └─────────┘
     │
     ▼
 ┌───────┐
 │ vault │  restore  ─▶ table-level Nickel re-import (+ KOReader if backed up)
 └───────┘
     │
     ▼
 ┌────────┐
 │ modder │  ─▶ mod catalogue, NickelMenu wizard, SSH, KOReader, Plato…
 └────────┘
```

Each step refuses to run until the previous one is recorded as done
(`$XDG_STATE_HOME/kobo_manager/<serial>.json`).

> ⚠️ **Firmware 5.x / 6.x is not supported, only monitored.** NickelMenu does not run on
> it, the 6.0 update repartitions the device and its betas lost reading stats.
> See `ROADMAP.md` → Known hazards.
>
> 🧪 **Theory first, practice last:** nothing writes to the real device until every step
> of the pipeline is implemented and tested on fake device trees.

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

## Project notes (decisions and findings, as of 2026-11-05)

A digest of the design discussions. `ROADMAP.md` holds the full backlog and the
references; this section explains *why* things are the way they are.

### Target device (read-only inspection, 2026-11-04)

- **Kobo Libra Colour** — serial prefix `N428`, codename *monza*, platform
  `mt8113t-ntx`, device id `…0390` (`.kobo/version` field 5). There is no "Libra Colour
  2", only a hardware revision **N428B** (bigger battery), same platform.
- Firmware **4.45.23684 → 4.46.23852** (latest 4.x). The device downloaded the 4.46 OTA
  by itself while plugged in; it was left to install. Nickel DB stays at `DbVersion 176`.
- Installed mods: NickelMenu **v0.5.4**, KFMon (disabled by the update), KOReader
  v2025.04 (installed but unused: 40 KB stats DB), Plato, NickelClock, KoboStuff's
  dropbear SSH (`.kobo/ssh-disabled` marker).
- `KoboReader.sqlite` is in **WAL** mode. Library: 200 books, 1354 reading events.
- User data not obvious at first: `fonts/`, `icons/`, exported annotations/notebooks,
  `.reading-states/`, `screen_*.png`, NickelMenu icons in `.adds/nm/.icon-*.png`.

### Decisions

| Topic | Decision |
|-------|----------|
| Hardware | `--hardware` on every CLI, default `libra-colour` (aliases `LibraColour`, `LibraColor`, `KoLC`); registry in `kobocore.hardware`, ready for more models. The KCC profile `KoLC` is shared with [manga_manager](https://github.com/burgesQ/manga_manager). |
| Firmware 5.x / 6.x | **Monitor only.** Stay on 4.x; `flasher watch` (to do) reports when NickelMenu, Nickelite, NickelHook Qt6, KOReader `kobov5` and KFMon are ready. |
| Device writes | **None until the whole pipeline is implemented** ("theory first"). Real device: read-only commands and `--dry-run` only. |
| Backup scope | User data + Nickel DB + mod configs. Books opt-in (`--with-books`, they live in Calibre). **KOReader opt-in** (`--with-koreader`), since it is unused. |
| Pending updates | Detected (`.kobo/KoboRoot.tgz`, `Kobo.tgz`, `update.tar`, `upgrade/`): `snapshot` warns, installers refuse to stage on top. |
| NickelMenu | Upgrade v0.5.4 → **v0.6.0** (pinned by sha256). Config regenerated by a wizard, split by feature, compatible with Nickelite syntax. |
| NickelMenu config review | KOReader/Plato launched via `cmd_spawn` (KOReader via KFMon **freezes on 4.46**); Telnet replaced by an SSH toggle; **FTP kept** (documented as insecure); "Invert & Reboot" removed; duplicates merged; screenshot via `nickel_screenshot:capture`; Google Drive added (not Instapaper, Pocket is dead); **debug items enabled**; footer active-icon path fixed (`.icon-coffee.png`); **Device Owner** message kept but stored only in `~/.config/kobo_manager/modder.toml`. |
| SSH | Everything runs as `root` (no useful other account; `/mnt/onboard` is FAT). Auth by **key or password** (`modder ssh auth key\|password`, default key) — needs the M11b spike on the device. Today dropbear runs with `-n` = **no password check**. |
| Mod catalogue | NickelMenu, KFMon, KOReader, Plato, NickelClock, NickelDBus, Rakuyomi, KOReader themes (appearance, SimpleUI, Project: Title); experimental: UltimateMangaReader, Banana Manga Reader; dormant (6.x): Nickelite. |
| Manga | **Rakuyomi** (KOReader plugin, active fork) is the recommended manga source reader; conversion stays in manga_manager (KCC). UltimateMangaReader 3.0 is greyscale-only and untested on Libra Colour → experimental only. |

### Research verdicts (checked 2026-11-04)

- **6.0** (Qt6, `update.tar`) is beta-only on Libra Colour, **repartitions the eMMC**
  (MBR → GPT) and its betas **lost reading stats and sideloaded highlights**; Kobo
  advises against rolling back.
- **NickelMenu** v0.6.0 has no 5.x/6.x support (draft Qt6 PR). **Nickelite** is the
  5.x/6.x successor (same `.adds/nm` syntax, exact-firmware packages, tested on Clara BW
  only). **NickelHook**'s `qt6-support` branch is what future mod ports will build on.
- **KOReader** has no official theme engine; themes are plugins (`appearance.koplugin`,
  SimpleUI, Project: Title) and user patches.
- `.kobo/ssh-disabled` is (re)created at boot by `/etc/init.d/ssh` (KoboStuff) unless
  `ssh-enabled` exists; the init script also wipes the root password unless
  `/.login_pass_set` exists.

### Implemented so far

| PR | Content |
|----|---------|
| #1 | GitHub setup: Dependabot (uv, actions, docker), CodeQL, secret scanning, private vulnerability reporting; CI (lint, mypy, tests on 3.12–3.14); uv-based Docker image on GHCR (deps cached in their own layer); Codespaces devcontainer; badges and topics. |
| #2 | Roadmap v2; `kobocore.hardware` + `--hardware`; shared CLI helpers `kobocore.cli` and exit codes `kobocore.exit_codes` (no more 4× duplicated code). |
| #3 | `vault snapshot` / `verify` / `export-stats`: scope selection, SQLite backup-API copies, sha256 manifest, `.partial` then rename, stats CSV/JSON, pending-update warning. First real backup taken and verified (47 files, 107.6 MiB). |
| #4 | `kobocore.mods` + `mods.toml` catalogue; `modder list`, `install` (NickelMenu 0.6.0), `wizard nickelmenu`, `ssh status\|enable\|disable\|keys`; every write is an op list (`modder.ops`) so `--dry-run` is uniform. Not yet run on the device. |

### Incidents and lessons

- **Tests wrote into the real `~/kobo-backups`** (fake serial only) — cleaned up; test
  suites now force `KOBO_BACKUP_ROOT`, `XDG_STATE_HOME`, `XDG_CONFIG_HOME` and
  `XDG_CACHE_HOME` into temp dirs.
- **The first snapshot most likely created `KoboReader.sqlite-wal`/`-shm` on the device**:
  Nickel's DB is in WAL mode and even a `mode=ro` SQLite connection creates those files.
  Harmless for Nickel (it uses WAL itself), but it broke the read-only promise. Fixed:
  databases are opened with `immutable=1` (a non-empty `-wal` is refused), backup copies
  are switched to `journal_mode=DELETE`, side files are excluded from snapshots.
- `.kobo/BookReader.sqlite` is not a SQLite database: copied raw, not integrity-checked.

### Next

1. `unmod` (data-driven from `mods.toml`), `flasher` (Kobo `UpgradeCheck` API, 4.x
   only) + `flasher watch`, `vault restore` (table-level, `DbVersion`-aware) — fake
   devices only.
2. KOReader wizard (themes, Rakuyomi), rest of the catalogue.
3. **Practice:** one real run of the whole safe path on the device, then the SSH spike
   (M11b: root by key or password).

## Development

```bash
make test
make lint
make type-check
```
