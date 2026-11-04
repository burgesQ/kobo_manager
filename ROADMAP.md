# Roadmap & Task Backlog

Safe path: **vault snapshot** → **vault verify** → **unmod** → **flasher** → **vault restore** → **modder**

Every step checks the previous one via the pipeline state (`kobocore.state`), so a
run can be resumed after an incident and steps can never run out of order.

Target hardware: **Kobo Libra Colour** (`--hardware libra-colour`, serial prefix `N428`,
codename *monza*, platform `mt8113t-ntx`, KCC profile `KoLC`). Books live in Calibre
(converted by [manga_manager](https://github.com/burgesQ/manga_manager) for manga); the
device is a cache — the irreplaceable data is **reading stats and progress**.

Device state at last inspection (2026-11-04): firmware **4.46.23852** (latest 4.x),
NickelMenu **v0.5.4**, KFMon (disabled by the 4.46 update), KOReader v2025.04 (unused),
Plato, NickelClock. Nickel DB `DbVersion=176`.

---

## ⚠️ Known hazards (read before touching anything)

- [ ] **H1** 🧨 **Firmware 5.x / 6.x is out of scope — monitor only.** The new line is
  **6.0** (Qt6, `update.tar` packages). On Libra Colour it is beta/opt-in only. The 6.0
  update **repartitions the eMMC (MBR → GPT) and moves the user FAT partition**; 6.0 betas
  **lost reading stats and sideloaded highlights**, and Kobo says rolling back deletes the
  missing data. NickelMenu and kobopatch do not run on it. `flasher` refuses
  `major > MAX_SAFE_MAJOR` (4); `flasher watch` (F6) reports when the mod ecosystem is ready.
- [ ] **H2** Auto-update is real: on 2026-11-04 the device staged 4.46 on its own
  (`.kobo/KoboRoot.tgz` + `.kobo/upgrade/`). Keep Wi-Fi / auto-sync off during the whole
  pipeline; log a warning in every CLI.
- [ ] **H3** Never overwrite a migrated `KoboReader.sqlite` with the pre-update copy —
  Nickel migrates the schema on first boot after an update.
- [ ] **H4** Never restore `Kobo eReader.conf` wholesale (account tokens, schema drift).
  Restore only selected keys.
- [ ] **H5** **Pending update detection**: if any of `.kobo/KoboRoot.tgz`,
  `.kobo/Kobo.tgz`, `.kobo/update.tar`, `.kobo/upgrade/` exists, an install is queued for
  the next eject. `vault snapshot` warns; every installer refuses to stage a package on top.
- [ ] **H6** **KOReader launched via KFMon freezes on Libra Colour 4.46**
  ([koreader#16333](https://github.com/koreader/koreader/issues/16333)); firmware updates
  also disable KFMon. Launch apps from NickelMenu `cmd_spawn`, not the KFMon generator.
- [ ] **H7** Remote shells: NiLuJe's dropbear/inetd package is **passwordless by default**;
  the current NickelMenu Telnet item exposes a plaintext root shell and the FTP item gives
  anonymous write access to the whole partition. Keys-only SSH, everything else opt-in.

---

## kobocore (shared lib, stdlib only)

- [x] **K1** Mount detection (`/media/$USER/KOBOeReader`, `/run/media/...`, `--mount`)
- [x] **K2** Parse `.kobo/version` → serial + firmware (`DeviceInfo`)
- [x] **K3** Pipeline state machine persisted in `$XDG_STATE_HOME/kobo_manager/<serial>.json`
- [x] **K4** Shared `ColorFormatter` logging + `--loglevel` / `--verbose`
- [x] **K5** Firmware version parsing + `is_mod_safe` guard (doctested)
- [x] **K6** (S) **Hardware registry** `kobocore.hardware`: `Hardware` (key, name, serial
  prefixes, device id, codename, platform, KCC profile, colour), `DEFAULT_HARDWARE =
  "libra-colour"`, alias normalisation (`LibraColour`, `LibraColor`, `KoLC`…). Covers the
  N428B revision. `--hardware` on every CLI; mismatch with the mounted device →
  `HARDWARE_MISMATCH` exit code.
- [ ] **K7** (S) Detect that Nickel is not mid-sync / the volume is mounted read-write
- [x] **K8** (M) `Manifest` dataclass shared by vault: file list, sha256, sizes, firmware,
  `DbVersion`, hardware key at backup time
- [x] **K9** (S) **Shared CLI helpers** `kobocore.cli`: `CLIError`, `add_common_args()`
  (`--mount`, `--dry-run`, `--hardware`, logging), `resolve_device()`, `check_phase()` —
  removes the four copies in `vault|unmod|flasher|modder`
- [ ] **K10** (M) **Mod compatibility matrix** `kobocore/data/mods.toml` (stdlib
  `tomllib`): per mod → firmware lines, launcher, install paths, uninstall method, upstream
  repo, `experimental` flag. Single source of truth for `unmod`, `modder`, `flasher watch`.
- [x] **K11** (S) Pending-update detector (H5) + `.kobo/version` field 5 (device id) parsing

## vault (backup / verify / restore / export)

### Short-term (high priority)

- [x] **V1** `snapshot` — timestamped copy into `~/kobo-backups/<serial>/<iso-date>/`
  (books excluded by default, `--with-books` to include). Scope:
  `.kobo/` (DBs, conf, screensaver), `fonts/`, `icons/`, `Exported Annotations/`,
  `Exported Notebooks/`, `.reading-states/`, `screen_*.png`, `.adds/nm/`,
  `.adds/kfmon/config/`, `.adds/nickelclock/settings.ini`, `.adds/plato/Settings.toml`
- [x] **V2** Consistent SQLite copies via the `sqlite3` backup API (not a raw file copy) for
  `.kobo/KoboReader.sqlite`
- [x] **V3** (optional, `--with-koreader`) KOReader state: `.adds/koreader/settings/`,
  `settings.reader.lua`, `statistics.sqlite3`, all `*.sdr/` sidecars. **Off by default** —
  KOReader is installed but unused.
- [x] **V4** Back up `.kobo/Kobo/Kobo eReader.conf` (never restored wholesale, H4)
- [x] **V5** Write `manifest.json` (K8) with sha256 for every file
- [x] **V6** `verify` — re-hash against manifest, `PRAGMA integrity_check` on each SQLite
  copy; only `verify` success marks `Phase.VERIFIED`
- [ ] **V7** Keep the **currently installed firmware zip** alongside the backup (fallback
  for a reflash of the same version)
- [ ] **V12** Write `.adds/kobo_manager/last_backup` (date + snapshot id) so NickelMenu can
  display it (M9 debug menu)

### Medium-term

- [ ] **V8** (optional) `restore` — KOReader side, only when V3 was taken
- [ ] **V9** `restore` — Nickel side: table-level re-import (reading progress, bookmarks,
  annotations, shelves) into the *migrated* DB, keyed by `ContentID`; never file
  overwrite (H3). Must handle `DbVersion` drift (176 on 4.46)
- [ ] **V10** `restore` — selective `Kobo eReader.conf` keys (H4), e.g. `ExcludeSyncFolders`
- [ ] **V11** `--dry-run` diff mode: show what would be restored, row counts per table

## export-stats (vault subcommand)

- [x] **S1** Export native Kobo stats (`Event`, `content` reading-time columns) to CSV/JSON
- [ ] **S2** (optional) Export KOReader stats (`book`, `page_stat_data`) to CSV/JSON
- [x] **S3** Run automatically at the end of `snapshot` — stats survive even if restore fails
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
- [ ] **U7** Data-driven removal from `mods.toml` (K10): Plato, NickelClock (`uninstall`
  marker), UltimateMangaReader (`.adds/UltimateMangaReader/`, `.adds/qt-6.*-kobo/`,
  `.adds/nm/_umr_conf`), Banana Manga Reader

## flasher

- [ ] **F1** Resolve the latest **4.x** firmware for the hardware from Kobo's
  `UpgradeCheck` API (`api.kobobooks.com/1.0/UpgradeCheck/Device/<device id>/kobo/<ver>/<serial>`;
  pgaskin's index stops at 4.44 for Libra Colour); hard-refuse 5.x/6.x (H1)
- [ ] **F2** Download + verify (size, zip integrity, hash if published)
- [ ] **F3** Stage the zip into `.kobo/` (refuse if H5 detects a pending update), then
  print the manual eject/wait instructions — flashing itself stays human-supervised
- [ ] **F4** Post-update check: re-read `.kobo/version`, confirm the expected version,
  mark `FLASHED`
- [ ] **F5** `--pin VERSION` to flash a specific known-good build
- [ ] **F6** **`flasher watch`** (read-only, network): latest 4.x vs newest line from
  the Kobo API, plus upstream readiness — NickelMenu releases & Qt6 PR #240, Nickelite
  releases (asset for the newest firmware? Libra Colour tested?), NickelHook
  `qt6-support` branch, KOReader `kobov5` builds, KFMon. Prints a readiness table.

## modder

### Core

- [ ] **M1** Install / upgrade NickelMenu (`KoboRoot.tgz` into `.kobo/`) — **v0.5.4 → v0.6.0**;
  handle the `.tar` vs `.tgz` naming trap from upstream downloads
- [ ] **M2** Install/upgrade KOReader into `.adds/koreader/` by **merge** (keep
  `settings/`, `patches/`, `icons/`, third-party plugins)
- [ ] **M3** Ensure `[FeatureSettings] ExcludeSyncFolders` in `Kobo eReader.conf` so Nickel
  does not index `.adds/` and KOReader dirs (already set on the device)
- [ ] **M5** Screensaver packs: copy user-supplied images (`assets/screensavers/<pack>/`)
- [ ] **M6** (spike) Transparent sleep screen on 4.46 (native setting vs patch vs NickelMenu)
- [ ] **M8** Compatibility check before install, driven by `mods.toml` (K10)
- [ ] **M17** CLI shape: `modder list` (installed vs matrix) · `modder install <mod>…` ·
  `modder wizard <name>`; stdlib `input()` prompts, `--non-interactive --config
  modder.toml` to replay; user config in `~/.config/kobo_manager/modder.toml`

### Wizards

- [ ] **M9** **NickelMenu wizard** (replaces M4). Ships a cleaned template split by feature
  (`.adds/nm/kobo_manager_{footer,launchers,network,power,library,reader,browser,debug}`),
  migrates the existing `qconf` (backed up, then disabled). Only emits syntax Nickelite
  also accepts. Decisions from the 2026-11-04 config review:
  - fix the footer active icon path (`.icon-coffee.png`, missing dot)
  - KOReader / Plato launchers via `cmd_spawn` (drop `generator:main:kfmon`, H6)
  - Telnet → **SSH toggle** (M11); **FTP kept** as opt-in, documented as insecure (H7)
  - remove `Invert Colors & Reboot`; merge duplicates (`Import books` = `Rescan Full`,
    double `IP Address` → one `wlan0`-only item; screenshot status+toggle →
    `nickel_screenshot:capture`)
  - **Debug menu enabled**: free memory, kernel, `df -h /mnt/onboard`, `uptime`,
    last backup (V12)
  - add `library:gdrive` (not Instapaper; `library:pocket` is dead since 4.38)
  - **Device Owner** message kept: text prompted once, stored in the local user config,
    **never committed** (public repo)
  - re-check the `menu_main_15505_<n>_enabled` button indexes on 4.46
  - opt-in presets: battery level, `selection_search` lookups (Wikipedia / DuckDuckGo /
    CNRTL), `auto_usb_gadget` toggle, lockscreen toggle, quick opens
    (`library:series|authors|shelves`, `reading_life:words`)
- [ ] **M10** **KOReader wizard**: install/upgrade (M2), theme plugins —
  [appearance.koplugin](https://github.com/Euphoriyy/appearance.koplugin) (one-tap themes),
  [SimpleUI](https://github.com/doctorhetfield-cmd/simpleui.koplugin),
  [Project: Title](https://github.com/joshuacant/ProjectTitle) (+ its fonts/icons) —
  user patches into `koreader/patches/`, "Start with" folder
- [ ] **M11** **SSH**: `modder ssh enable|disable|status`. Spike first: identify what
  ships `.kobo/ssh-disabled` (rename to `ssh-enabled` + reboot) and the dropbear in use.
  Install `authorized_keys` from `~/.ssh/*.pub`, disable password login, NickelMenu toggle.
  KOReader's SSH plugin (port 2222, only while KOReader runs) is the fallback.

### Catalogue (entries in `mods.toml`)

- [ ] **M12** [Rakuyomi](https://github.com/tachibana-shin/rakuyomi) manga plugin for
  KOReader (upstream archived 2026-01 → active fork): `plugins/rakuyomi.koplugin` +
  `rakuyomi/settings.json` (source lists, languages). Verify Kindle vs KindleHF build on device
- [ ] **M13** [Plato](https://github.com/baskerville/plato) reader (already installed),
  launched from NickelMenu
- [ ] **M14** NickelClock (installed) and NickelDBus (scripts can drive Nickel)
- [ ] **M15** (experimental, off by default) standalone manga readers:
  [UltimateMangaReader](https://github.com/Rain92/UltimateMangaReader) 3.0 (Qt6 rewrite,
  greyscale only, Libra Colour untested) and Banana Manga Reader (inactive since ~2023)
- [ ] **M16** (dormant, 6.x only) [Nickelite](https://github.com/open-source-arena/Nickelite)
  — NickelMenu successor for firmware 5+/6.0, same `.adds/nm` syntax, exact-firmware
  pinned `.kobo/Kobo.tgz` packages. Enabled only if we ever leave 4.x (H1, F6)

---

## CI / DevOps

- [x] **CI1** Device tests marked `@pytest.mark.device`, never run in CI
- [x] **CI2** Fake-Kobo fixture tree with a real (tiny) `KoboReader.sqlite` schema for V9 tests
- [x] **CI3** Lint is a real gate from day one (no `|| true`)
- [ ] **CI4** Coverage threshold gate

## Code Quality

- [ ] **Q1** Unified `kobo backup|unmod|flash|restore|mod` dispatcher + `kobo run` that
  walks the whole safe path with confirmations
- [ ] **Q2** Rich-free progress output (stdlib only), consistent emoji prefixes
- [ ] **Q3** Package READMEs once each CLI is implemented

---

## Execution order

**Theory first, practice last.** Every write path (unmod, flasher, restore, modder) is
built and tested against fake device trees only. Against the real Kobo, only read-only
commands run (`vault snapshot|verify|export-stats`, `--dry-run`). The real run — unmod,
flash, restore, mods — happens in one go once the whole pipeline is implemented.

1. ✅ **K9 + K6** shared CLI helpers and `--hardware`
2. ✅ **K8, K11, V1–V6, S1, S3** — snapshot/verify (first real backup taken on 4.46,
   read-only)
3. **K10 → M1 → M9 → M11** — mod matrix, NickelMenu 0.6.0 + wizard (fixes the
   KOReader/Plato launchers broken by 4.46), SSH — fake devices only
4. **U1–U7 → F1–F6 → V7–V11, V12** — unmod, flasher 4.x + `watch`, restore — fake devices only
5. **M10, M12–M15** — KOReader wizard, catalogue
6. 🎯 **Practice**: real run of the safe path on the device

---

## References (checked 2026-11-04)

- Kobo firmware & 6.0: [Kobo help — missing data after 6.0 beta](https://help.kobo.com/hc/en-us/articles/43753873356055-Missing-books-reading-stats-or-notes-after-Kobo-software-update),
  [Notebookcheck on 6.0 beta](https://www.notebookcheck.net/Kobo-6-0-beta-update-renders-certain-e-readers-unusable.1409928.0.html),
  [KoboTolinoFindings](https://github.com/notmarek/KoboTolinoFindings),
  [pgaskin firmware index](https://pgaskin.net/KoboStuff/kobofirmware.html),
  [N428B revision](https://blog.the-ebook-reader.com/2025/12/03/kobo-libra-colour-revision-n428b-has-larger-battery/)
- NickelMenu: [site & doc](https://pgaskin.net/NickelMenu/), [releases](https://github.com/pgaskin/NickelMenu/releases),
  [Qt6 port discussion #230](https://github.com/pgaskin/NickelMenu/issues/230), [draft PR #240](https://github.com/pgaskin/NickelMenu/pull/240)
- Nickelite: [repo](https://github.com/open-source-arena/Nickelite) ·
  NickelHook Qt6: [nicoverbruggen/NickelHook `qt6-support`](https://github.com/nicoverbruggen/NickelHook/tree/qt6-support)
- KOReader: [releases](https://github.com/koreader/koreader/releases),
  [Kobo install wiki](https://github.com/koreader/koreader/wiki/Installation-on-Kobo-devices),
  [SSH wiki](https://github.com/koreader/koreader/wiki/SSH),
  [4.46 KFMon freeze #16333](https://github.com/koreader/koreader/issues/16333)
- KFMon: [repo](https://github.com/NiLuJe/kfmon) · NiLuJe one-click package and "Kobo stuff":
  [MobileRead t=314220](https://www.mobileread.com/forums/showthread.php?t=314220),
  [MobileRead p=3021983](https://www.mobileread.com/forums/showthread.php?p=3021983)
- kobopatch: [kobopatch-webui](https://github.com/nicoverbruggen/kobopatch-webui)
- Manga: [UltimateMangaReader 3.0.0](https://github.com/Rain92/UltimateMangaReader/releases/tag/3.0.0),
  [Rakuyomi (archived)](https://github.com/hanatsumi/rakuyomi), [Rakuyomi fork](https://github.com/tachibana-shin/rakuyomi),
  [Banana Manga Reader thread](https://www.mobileread.com/forums/showthread.php?p=4333172)
