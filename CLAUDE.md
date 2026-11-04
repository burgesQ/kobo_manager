# CLAUDE.md

Guidance for Claude Code sessions in this repository.

## Project Overview

`kobo_manager` is a Python 3.12+ uv workspace of CLI tools to safely update a modded
Kobo e-reader without losing reading stats. Target hardware is selected with
`--hardware` (default `libra-colour`: Kobo Libra Colour, serial prefix `N428`); the
registry lives in `kobocore.hardware`.

**Safe path:**

```
vault snapshot → vault verify → unmod → flasher → vault restore → modder
```

| Package    | Kind | Purpose |
|------------|------|---------|
| `kobocore` | lib  | Mount detection, `.kobo/version` parsing, hardware registry, firmware guard, pipeline state, shared CLI helpers (`kobocore.cli`), logging |
| `vault`    | CLI  | `snapshot` / `verify` / `restore` / `export-stats` |
| `unmod`    | CLI  | Remove NickelMenu, KFMon, `KoboRoot.tgz`, patches, other mods (keeps KOReader) |
| `flasher`  | CLI  | Fetch / verify / stage official **4.x** firmware; `watch` for 5.x/6.x readiness |
| `modder`   | CLI  | Mod catalogue + wizards (NickelMenu, KOReader, SSH, Plato, Rakuyomi…) |

- **All packages are stdlib-only** except `shtab` for completion. Keep it that way.
- **Platform:** Linux.

## Hard rules (safety)

- **Never flash firmware 5.x / 6.x.** `kobocore.firmware.MAX_SAFE_MAJOR = 4`; the new
  line is monitored only (`flasher watch`). See ROADMAP H1.
- **Never stage a package while an update is pending** (`.kobo/KoboRoot.tgz`,
  `Kobo.tgz`, `update.tar`, `upgrade/`). See ROADMAP H5.
- **Never commit personal data** read from the device (e.g. the NickelMenu "Device
  Owner" text): it belongs in `~/.config/kobo_manager/`. The repo is public.
- **Never overwrite `KoboReader.sqlite`** after an update; restore at table level only.
- **Never write to Calibre's `metadata.db` directly** — use `calibredb`.
- Every write operation supports `--dry-run` (log intent, touch nothing).
- Every phase calls `PipelineState.require()` before acting and `mark()` only on success.

## Device layout (paths relative to the mount)

| Path | Content |
|------|---------|
| `.kobo/version` | serial, firmware, device id (comma-separated, fields 0, 2 and 5) |
| `.kobo/KoboReader.sqlite` | Nickel DB: progress, bookmarks, shelves, stats |
| `.kobo/Kobo/Kobo eReader.conf` | settings + account (never restore wholesale) |
| `.adds/koreader/` | KOReader install |
| `.adds/koreader/settings/statistics.sqlite3` | KOReader reading stats (backup opt-in: `--with-koreader`) |
| `*.sdr/` next to books | KOReader per-book sidecars (progress, highlights) |
| `.adds/nm/` | NickelMenu config; `uninstall` file here triggers removal on reboot |
| `.adds/kfmon/` | KFMon launcher (disabled by firmware updates; avoid for KOReader on 4.46, H6) |
| `.adds/plato/`, `.adds/nickelclock/` | Plato reader, NickelClock (`uninstall` marker) |
| `.kobo/KoboRoot.tgz`, `.kobo/upgrade/` | pending update, applied on next eject (H5) |

## Code Conventions (inherited from manga_manager)

- **argparse** only (no click/typer); `--version`, `--print-completion` (shtab)
- **`CLIError` early-exit pattern** (`kobocore.cli`): helpers log then raise
  `CLIError(code)`; `main()` stays a flat orchestrator. Common args (`--mount`,
  `--dry-run`, `--hardware`, logging) come from `kobocore.cli.add_common_args()`
- **Named exit codes** in each package's `exit_codes.py` — never bare integers
- **NamedTuple** for structured returns, **dataclass** for config, **`pathlib.Path`** only
- **Logging** via `kobocore.log` (`ColorFormatter`, emoji prefixes); never `print()`
- Doctests on pure helpers (run via `pytest --doctest-modules`)
- Factory-pattern fixtures in `conftest.py` (`make_kobo(root, firmware=...)`)
- Tests call `main()` directly for coverage; real-device tests use `@pytest.mark.device`
- `setup_logging()` clears root handlers → use `capsys.readouterr().err`, not `caplog`,
  for CLI-level log assertions
- Line length 88 (Black); mypy strict

## Dev Commands

```bash
uv sync
make test           # uv run pytest .
make lint           # ruff + black + isort (check)
make lint-fix
make type-check     # mypy strict on all packages
uv run vault snapshot --dry-run --verbose
```

## Roadmap

See `ROADMAP.md` → *Execution order*. Nothing writes to the device until a verified
backup exists (V1–V6).
