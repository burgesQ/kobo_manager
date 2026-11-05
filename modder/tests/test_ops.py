from pathlib import Path

from modder.ops import CopyIn, Move, WriteText, apply, describe


def test_apply_runs_every_op(tmp_path: Path) -> None:
    mount = tmp_path / "K"
    (mount / ".adds/nm").mkdir(parents=True)
    (mount / ".adds/nm/qconf").write_text("legacy")
    local = tmp_path / "pkg.tgz"
    local.write_bytes(b"pkg")
    apply(
        mount,
        [
            WriteText(Path(".adds/nm/kobo_manager_power"), "menu_item:main:A:b:c\n"),
            Move(Path(".adds/nm/qconf"), Path(".adds/kobo_manager/nm-disabled/qconf")),
            CopyIn(local, Path(".kobo/KoboRoot.tgz")),
        ],
        dry_run=False,
    )
    assert (mount / ".adds/nm/kobo_manager_power").read_text().startswith("menu_item")
    assert not (mount / ".adds/nm/qconf").exists()
    assert (mount / ".adds/kobo_manager/nm-disabled/qconf").read_text() == "legacy"
    assert (mount / ".kobo/KoboRoot.tgz").read_bytes() == b"pkg"


def test_dry_run_touches_nothing(tmp_path: Path) -> None:
    mount = tmp_path / "K"
    mount.mkdir()
    apply(mount, [WriteText(Path("a/b"), "x")], dry_run=True)
    assert list(mount.iterdir()) == []


def test_describe() -> None:
    assert describe(Move(Path("a"), Path("b"))) == "move a -> b"
