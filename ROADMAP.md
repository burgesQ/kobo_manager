# Roadmap & Task Backlog

Safe path: **vault snapshot** → **vault verify** → **unmod** → **flasher** → **vault restore** → **modder**

Every step checks the previous one via the pipeline state (`kobocore.state`), so a
run can be resumed after an incident and steps can never run out of order.

Target device: **Kobo Libra Colour** (serial prefix `N428`). Books live in Calibre;
the device is a cache — the irreplaceable data is **reading stats and progress**.

---

## ⚠️ Known hazards (read before touching anything)

- [ ] **H1** 🧨 **Firmware 5.x kills the mod step.** Kobo ships a Qt6-based 5.x line on
  Libra Colour / Clara Colour / Clara BW. NickelMenu does not work on 5.x, the update
  mechanism changed (`update.tar` instead of `KoboRoot.tgz`), and downgrading from 5.x
  has been reported to boot-loop. **"Latest firmware" means "latest 4.45.x".**
  `flasher` must refuse `major >= 5` (`kobocore.firmware.MAX_SAFE_MAJOR`) unless an
  explicit, scary override flag is passed.
- [ ] **H2** Disable auto-update / keep Wi-Fi off during the whole pipeline, otherwise
  Nickel may pull 5.x by itself between two steps. Document it as a manual checklist item
  and log a warning in every CLI.
- [ ] **H3** Never overwrite a migrated `KoboReader.sqlite` with the pre-update copy —
  Nickel migrates the schema on first boot after an update.
- [ ] **H4** Never restore `Kobo eReader.conf` wholesale (account tokens, schema drift).
  Restore only selected keys.

---

## kobocore (shared lib, stdlib only)

- [x] **K1** Mount detection (`/media/$USER/KOBOeReader`, `/run/media/...`, `--mount`)
- [x] **K2** Parse `.kobo/version` → serial + firmware (`DeviceInfo`)
- [x] **K3** Pipeline state machine persisted in `$XDG_STATE_HOME/kobo_manager/<serial>.json`
- [x] **K4** Shared `ColorFormatter` logging + `--loglevel` / `--verbose`
- [x] **K5** Firmware version parsing + `is_mod_safe` guard (doctested)
- [ ] **K6** (S) Refuse to run if the serial prefix is not a known/tested model (`N428`),
  overridable with `--force-model`
- [ ] **K7** (S) Detect that Nickel is not mid-sync / the volume is mounted read-write
- [ ] **K8** (M) `Manifest` dataclass shared by vault: file list, sha256, sizes, fw version
  at backup time

## vault (backup / verify / restore / export)

### Short-term (high priority)

- [ ] **V1** `snapshot` — timestamped full copy of the user partition into
  `~/kobo-backups/<serial>/<iso-date>/` (books excluded by default, `--with-books` to include)
- [ ] **V2** Consistent SQLite copies via the `sqlite3` backup API (not a raw file copy) for
  `.kobo/KoboReader.sqlite` and `.adds/koreader/settings/statistics.sqlite3`
- [ ] **V3** Back up KOReader state: `.adds/koreader/settings/`, `settings.reader.lua`,
  and **all `*.sdr/` sidecar dirs** (they sit next to the books by default — easy to miss)
- [ ] **V4** Back up `.kobo/Kobo/Kobo eReader.conf`, `.adds/nm/` config, screensaver dir
- [ ] **V5** Write `manifest.json` (K8) with sha256 for every file
- [ ] **V6** `verify` — re-hash against manifest, `PRAGMA integrity_check` on each SQLite
  copy; only `verify` success marks `Phase.VERIFIED`
- [ ] **V7** Keep the **currently installed firmware zip** alongside the backup (fallback
  for a reflash of the same version)

### Medium-term

- [ ] **V8** `restore` — KOReader side: copy back `statistics.sqlite3`, settings, sidecars
  (safe: independent of Nickel)
- [ ] **V9** `restore` — Nickel side: table-level re-import (reading progress, bookmarks,
  annotations, shelves) into the *migrated* DB, keyed by `ContentID`; never file overwrite (H3)
- [ ] **V10** `restore` — selective `Kobo eReader.conf` keys (H4), e.g. `ExcludeSyncFolders`
- [ ] **V11** `--dry-run` diff mode: show what would be restored, row counts per table

## export-stats (vault subcommand)

- [ ] **S1** Export native Kobo stats (`Event`, `content` reading-time columns) to CSV/JSON
- [ ] **S2** Export KOReader stats (`book`, `page_stat_data`) to CSV/JSON
- [ ] **S3** Run automatically at the end of `snapshot` — stats survive even if restore fails
- [ ] **S4** (M) Match device books to Calibre (`metadata.db`, read-only) by title/author/UUID
- [ ] **S5** (M) Push per-book stats into the existing Calibre custom columns (write via
  `calibredb set_custom`, never direct SQL on `metadata.db`)
- [ ] **S6** (L) Dashboard (time per day, pages/hour, streaks) — maybe a separate package

## unmod

- [ ] **U1** NickelMenu: create `.adds/nm/uninstall` and ask for a reboot (official method)
- [ ] **U2** Remove KFMon (`.adds/kfmon/`, launcher PNGs) — it does not survive updates anyway
- [ ] **U3** Detect and remove leftover `.kobo/KoboRoot.tgz` (re-applied on every boot otherwise)
- [ ] **U4** Detect kobopatch / custom patches; revert path = reflash stock firmware
- [ ] **U5** **Keep KOReader** (`.adds/koreader/`) — independent of Nickel, emergency reader
- [ ] **U6** Post-reboot check: confirm NickelMenu entry is gone before marking `UNMODDED`

## flasher

- [ ] **F1** Resolve the latest **4.x** firmware for the device model (source: Patrick
  Gaskin's Kobo firmware index), hard-refuse 5.x (H1)
- [ ] **F2** Download + verify (size, zip integrity, hash if published)
- [ ] **F3** Stage the zip into `.kobo/`, then print the manual eject/wait instructions —
  flashing itself stays human-supervised
- [ ] **F4** Post-update check: re-read `.kobo/version`, confirm the expected version,
  mark `FLASHED`
- [ ] **F5** `--pin VERSION` to flash a specific known-good build (e.g. one where NickelMenu
  is confirmed working)

## modder

- [ ] **M1** Install NickelMenu (`KoboRoot.tgz` into `.kobo/`); handle the `.tar` vs `.tgz`
  naming trap from upstream downloads
- [ ] **M2** Install/upgrade KOReader into `.adds/koreader/` (preserve `settings/`)
- [ ] **M3** Ensure `[FeatureSettings] ExcludeSyncFolders` in `Kobo eReader.conf` so Nickel
  does not index `.adds/` and KOReader dirs
- [ ] **M4** Ship a default NickelMenu config (`.adds/nm/config`) from the repo
- [ ] **M5** Screensaver packs: copy user-supplied images (`assets/screensavers/<pack>/`)
- [ ] **M6** (spike) Transparent sleep screen — find the cleanest way on 4.45.x
  (native setting vs patch vs NickelMenu action)
- [ ] **M7** (spike) "What's fun now" — survey current community mods compatible with 4.45.x
- [ ] **M8** Compatibility matrix in YAML (`mods.yaml`: mod → min/max firmware) checked
  before install

---

## CI / DevOps

- [ ] **CI1** Device tests marked `@pytest.mark.device`, never run in CI
- [ ] **CI2** Fake-Kobo fixture tree with a real (tiny) `KoboReader.sqlite` schema for V9 tests
- [ ] **CI3** Lint is a real gate from day one (no `|| true`)
- [ ] **CI4** Coverage threshold gate

## Code Quality

- [ ] **Q1** Unified `kobo backup|unmod|flash|restore|mod` dispatcher + `kobo run` that
  walks the whole safe path with confirmations
- [ ] **Q2** Rich-free progress output (stdlib only), consistent emoji prefixes
- [ ] **Q3** Package READMEs once each CLI is implemented
