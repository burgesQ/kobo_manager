# CLAUDE.md

Guidance for Claude Code sessions in this repository.

## Project Overview

`kobo_manager` is a Python 3.12+ uv workspace of CLI tools to safely update a modded
Kobo e-reader (target: Libra Colour, serial prefix `N428`) without losing reading stats.

**Safe path:**

```
vault snapshot → vault verify → unmod → flasher → vault restore → modder
```

| Package    | Kind | Purpose |
|------------|------|---------|
| `kobocore` | lib  | Mount detection, `.kobo/version` parsing, firmware guard, pipeline state, logging |
| `vault`    | CLI  | `snapshot` / `verify` / `restore` / `export-stats` |
| `unmod`    | CLI  | Remove NickelMenu, KFMon, `KoboRoot.tgz`, patches (keeps KOReader) |
| `flasher`  | CLI  | Fetch / verify / stage official **4.x** firmware |
| `modder`   | CLI  | Install KOReader, NickelMenu, screensavers, config |

- **All packages are stdlib-only** except `shtab` for completion. Keep it that way.
- **Platform:** Linux.

## Hard rules (safety)

- **Never flash firmware 5.x.** `kobocore.firmware.MAX_SAFE_MAJOR = 4`. See ROADMAP H1.
- **Never overwrite `KoboReader.sqlite`** after an update; restore at table level only.
- **Never write to Calibre's `metadata.db` directly** — use `calibredb`.
- Every write operation supports `--dry-run` (log intent, touch nothing).
- Every phase calls `PipelineState.require()` before acting and `mark()` only on success.

## Device layout (paths relative to the mount)

| Path | Content |
|------|---------|
| `.kobo/version` | serial, firmware (comma-separated, fields 0 and 2) |
| `.kobo/KoboReader.sqlite` | Nickel DB: progress, bookmarks, shelves, stats |
| `.kobo/Kobo/Kobo eReader.conf` | settings + account (never restore wholesale) |
| `.adds/koreader/` | KOReader install |
| `.adds/koreader/settings/statistics.sqlite3` | KOReader reading stats |
| `*.sdr/` next to books | KOReader per-book sidecars (progress, highlights) |
| `.adds/nm/` | NickelMenu config; `uninstall` file here triggers removal on reboot |
| `.adds/kfmon/` | KFMon launcher |

## Code Conventions (inherited from manga_manager)

- **argparse** only (no click/typer); `--version`, `--print-completion` (shtab)
- **`_CLIError` early-exit pattern**: helpers log then raise `_CLIError(code)`; `main()`
  stays a flat orchestrator
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

See `ROADMAP.md`. Start with **V1–V6 + S1–S3** (backup, verify, stats export): nothing
else is allowed to run until a verified backup exists.
