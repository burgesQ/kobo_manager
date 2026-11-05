"""modder CLI: mod catalogue, installs and wizards."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import Any

import shtab

from kobocore.cli import CLIError, add_common_args, check_phase, resolve_device
from kobocore.device import DeviceInfo, pending_updates
from kobocore.log import setup_logging
from kobocore.mods import Mod, installed_mods, load_catalogue
from kobocore.state import Phase, PipelineState
from modder import nickelmenu, ssh
from modder.exit_codes import (
    CLI_ERROR,
    INVALID_PACKAGE,
    NOT_IMPLEMENTED,
    PROCESSING_ERROR,
    SUCCESS,
    UNSAFE_FIRMWARE,
    UPDATE_PENDING,
)
from modder.install import (
    PackageError,
    cache_dir,
    fetch_package,
    stage_ops,
    validate_package,
)
from modder.ops import Op, apply
from modder.prompt import ask_text, ask_yes_no
from modder.userconfig import config_path, load_config, save_config

logger = logging.getLogger(__name__)

Handler = Callable[[argparse.Namespace, DeviceInfo, PipelineState], int]
CATALOGUE = load_catalogue()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="modder",
        description="Mod catalogue, installs and setup wizards for a Kobo",
    )
    parser.add_argument("--version", action="version", version=version("modder"))
    shtab.add_argument_to(parser, "--print-completion")
    sub = parser.add_subparsers(dest="command", required=True)

    add_common_args(sub.add_parser("list", help="catalogue vs installed mods"))

    install = sub.add_parser("install", help="stage a pinned mod package")
    add_common_args(install)
    install.add_argument("mod", choices=sorted(CATALOGUE))
    install.add_argument("--package", type=Path, help="local package (else download)")
    install.add_argument(
        "--experimental", action="store_true", help="allow experimental mods"
    )

    wizard = sub.add_parser("wizard", help="interactive setup")
    add_common_args(wizard)
    wizard.add_argument("name", choices=["nickelmenu"])
    wizard.add_argument(
        "--non-interactive",
        action="store_true",
        help=f"no prompts: use defaults + {config_path()}",
    )

    ssh_p = sub.add_parser("ssh", help="SSH server marker and keys")
    ssh_sub = ssh_p.add_subparsers(dest="ssh_command", required=True)
    for name in ("status", "enable", "disable"):
        add_common_args(ssh_sub.add_parser(name))
    keys = ssh_sub.add_parser("keys", help="install public keys")
    add_common_args(keys)
    keys.add_argument(
        "--pubkey", type=Path, action="append", help="default: ~/.ssh/*.pub"
    )
    return parser


def _apply(mount: Path, ops: list[Op], args: argparse.Namespace) -> None:
    try:
        apply(mount, ops, dry_run=args.dry_run)
    except OSError as exc:
        logger.error("write failed: %s", exc)
        raise CLIError(PROCESSING_ERROR) from exc


def _done(state: PipelineState, args: argparse.Namespace) -> int:
    state.mark(Phase.MODDED, dry_run=args.dry_run)
    return SUCCESS


def _list(args: argparse.Namespace, device: DeviceInfo, state: PipelineState) -> int:
    installed = {m.key for m in installed_mods(device.mount, CATALOGUE)}
    for mod in CATALOGUE.values():
        lines = "/".join(f"{n}.x" for n in mod.lines)
        flags = [
            "installed" if mod.key in installed else "-",
            "ok" if mod.supports(device.firmware) else f"not on {device.firmware}",
        ]
        if mod.experimental:
            flags.append("experimental")
        logger.info("%-20s %-22s %-11s %s", mod.key, mod.name, lines, ", ".join(flags))
    return SUCCESS


def _resolve_package(mod: Mod, args: argparse.Namespace) -> Path:
    if args.package is not None:
        return Path(args.package)
    try:
        return fetch_package(mod, cache_dir())
    except PackageError as exc:
        logger.error("%s", exc)
        raise CLIError(INVALID_PACKAGE) from exc
    except OSError as exc:
        logger.error("download failed: %s", exc)
        raise CLIError(PROCESSING_ERROR) from exc


def _install(args: argparse.Namespace, device: DeviceInfo, state: PipelineState) -> int:
    check_phase(state, Phase.MODDED)
    mod = CATALOGUE[args.mod]
    if mod.experimental and not args.experimental:
        logger.error("%s is experimental: pass --experimental", mod.name)
        raise CLIError(CLI_ERROR)
    if not mod.supports(device.firmware):
        logger.error("%s does not support firmware %s", mod.name, device.firmware)
        raise CLIError(UNSAFE_FIRMWARE)
    if not mod.package:
        logger.warning("no automated install for %s yet (see ROADMAP)", mod.name)
        return NOT_IMPLEMENTED
    if pending := pending_updates(device.mount):
        logger.error(
            "update already staged (%s): eject first (ROADMAP H5)",
            ", ".join(map(str, pending)),
        )
        raise CLIError(UPDATE_PENDING)
    package = _resolve_package(mod, args)
    try:
        validate_package(mod, package)
        ops = stage_ops(mod, package)
    except PackageError as exc:
        logger.error("%s", exc)
        raise CLIError(INVALID_PACKAGE) from exc
    _apply(device.mount, ops, args)
    logger.info("eject the Kobo: Nickel installs %s and reboots", mod.name)
    return _done(state, args)


def _wizard(args: argparse.Namespace, device: DeviceInfo, state: PipelineState) -> int:
    check_phase(state, Phase.MODDED)
    path = config_path()
    config = load_config(path)
    saved: dict[str, Any] = config.get("nickelmenu", {})
    interactive = not args.non_interactive
    ask = ask_yes_no if interactive else None

    owner = str(saved.get("owner", ""))
    if interactive:
        owner = ask_text("Device owner message (empty for none)", owner)
    installed = {m.key for m in installed_mods(device.mount, CATALOGUE)}
    offered = nickelmenu.available(installed)
    chosen = nickelmenu.choose(
        offered, set(saved.get("enabled", [])), set(saved.get("disabled", [])), ask
    )
    if owner:
        chosen.append(
            next(p for p in nickelmenu.PRESETS if p.id == nickelmenu.OWNER_ID)
        )
    migrate = [
        name
        for name in nickelmenu.legacy_files(device.mount)
        if (
            ask(f"move legacy .adds/nm/{name} out of NickelMenu?", True)
            if ask
            else bool(saved.get("migrate_legacy", True))
        )
    ]
    for icon in nickelmenu.missing_icons(device.mount, chosen):
        logger.warning("icon .adds/nm/%s is missing on the device", icon)

    _apply(device.mount, nickelmenu.plan(device.mount, chosen, owner, migrate), args)
    if interactive and not args.dry_run:
        ids = [p.id for p in chosen]
        saved.update(
            owner=owner,
            enabled=ids,
            disabled=[p.id for p in offered if p.id not in ids],
        )
        config["nickelmenu"] = saved
        save_config(config, path)
        logger.info("answers saved to %s", path)
    logger.info("NickelMenu reloads its config by itself (no reboot needed)")
    return _done(state, args)


def _ssh(args: argparse.Namespace, device: DeviceInfo, state: PipelineState) -> int:
    mount = device.mount
    if args.ssh_command == "status":
        current = ssh.state(mount)
        logger.info("system sshd marker: %s", current)
        if current is ssh.SshState.ENABLED:
            logger.warning("dropbear runs with -n: no password check (ROADMAP H7)")
        logger.info(
            "KOReader SSH plugin: %s, keys: %s",
            "present" if (mount / ssh.KOREADER_DIR).is_dir() else "absent",
            "yes" if (mount / ssh.KOREADER_KEYS).is_file() else "no",
        )
        return SUCCESS

    check_phase(state, Phase.MODDED)
    try:
        if args.ssh_command == "keys":
            keys = ssh.read_pubkeys(args.pubkey or ssh.default_pubkeys())
            ops = ssh.keys_ops(mount, keys)
        else:
            ops = ssh.toggle_ops(mount, enable=args.ssh_command == "enable")
    except (ssh.SshError, OSError) as exc:
        logger.error("%s", exc)
        raise CLIError(PROCESSING_ERROR) from exc
    _apply(mount, ops, args)
    if args.ssh_command == "enable":
        logger.warning("dropbear runs with -n: no password check (ROADMAP H7)")
    if args.ssh_command in {"enable", "disable"}:
        logger.info("reboot the Kobo to apply")
    return _done(state, args)


_HANDLERS: dict[str, Handler] = {
    "list": _list,
    "install": _install,
    "wizard": _wizard,
    "ssh": _ssh,
}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    setup_logging(args)
    try:
        device = resolve_device(args)
        return _HANDLERS[args.command](args, device, PipelineState(device.serial))
    except CLIError as exc:
        return exc.code
