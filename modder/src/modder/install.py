"""Fetch, validate and stage a pinned mod package (ROADMAP M1)."""

from __future__ import annotations

import gzip
import logging
import os
import tarfile
import urllib.request
from collections.abc import Callable
from pathlib import Path

from kobocore.manifest import sha256_file
from kobocore.mods import Mod
from modder.ops import CopyIn, Op

logger = logging.getLogger(__name__)

KOBOROOT = Path(".kobo/KoboRoot.tgz")
_GZIP_MAGIC = b"\x1f\x8b"

Downloader = Callable[[str, Path], None]


class PackageError(ValueError):
    """The package is not the mod it claims to be."""


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "kobo_manager"


def _download(url: str, dest: Path) -> None:
    logger.info("downloading %s", url)
    with urllib.request.urlopen(url, timeout=60) as resp:
        dest.write_bytes(resp.read())


def fetch_package(mod: Mod, cache: Path, download: Downloader = _download) -> Path:
    """Return the cached release asset, downloading it if needed; checks sha256."""
    if not mod.download_url:
        raise PackageError(f"{mod.name} has no pinned package to download")
    dest = cache / mod.key / mod.version / mod.package
    if not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_name(dest.name + ".part")
        download(mod.download_url, partial)
        partial.replace(dest)
    digest = sha256_file(dest)
    if mod.sha256 and digest != mod.sha256:
        dest.unlink()
        raise PackageError(
            f"{mod.package}: sha256 {digest} does not match pinned {mod.sha256}"
        )
    return dest


def _member_names(package: Path) -> set[str]:
    with tarfile.open(package, "r:gz") as tar:
        return {name.removeprefix("./") for name in tar.getnames()}


def validate_package(mod: Mod, package: Path) -> None:
    """Gzip tarball (whatever its extension) containing the mod's marker file.

    Browsers often save ``KoboRoot.tgz`` as ``KoboRoot.tar``: the name is ignored,
    the content decides.
    """
    with package.open("rb") as fh:
        if fh.read(2) != _GZIP_MAGIC:
            raise PackageError(f"{package.name} is not a gzip archive")
    try:
        names = _member_names(package)
    except (tarfile.TarError, gzip.BadGzipFile, EOFError) as exc:
        raise PackageError(f"{package.name}: {exc}") from exc
    if mod.package_marker not in names:
        raise PackageError(
            f"{package.name} does not contain {mod.package_marker}: not {mod.name}"
        )
    if mod.sha256 and sha256_file(package) != mod.sha256:
        logger.warning(
            "%s differs from the pinned %s v%s release", package, mod.name, mod.version
        )


def stage_ops(mod: Mod, package: Path) -> list[Op]:
    if mod.kind != "nickel-mod":
        raise PackageError(f"{mod.name}: only KoboRoot.tgz mods can be staged")
    return [CopyIn(package, KOBOROOT)]
