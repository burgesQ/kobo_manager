from pathlib import Path

from vault.scope import ScopeOptions, select_files


def _selected(mount: Path, **opts: bool) -> set[str]:
    return {p.as_posix() for p in select_files(mount, ScopeOptions(**opts))}


def test_default_scope_keeps_user_data(tmp_path: Path, make_kobo) -> None:
    files = _selected(make_kobo(tmp_path, populated=True))
    for rel in [
        ".kobo/version",
        ".kobo/KoboReader.sqlite",
        ".kobo/Kobo/Kobo eReader.conf",
        ".kobo/screensaver/sleep.png",
        "fonts/Bookerly.ttf",
        "icons/coffee.png",
        "Exported Annotations/notes.txt",
        ".adds/nm/qconf",
        ".adds/kfmon/config/kfmon.ini",
        ".adds/nickelclock/settings.ini",
        ".adds/plato/Settings.toml",
        "screen_001.png",
        "metadata.calibre",
    ]:
        assert rel in files, rel


def test_default_scope_skips_books_caches_and_koreader(
    tmp_path: Path, make_kobo
) -> None:
    files = _selected(make_kobo(tmp_path, populated=True))
    for rel in [
        ".kobo/dict/dicthtml-fr.zip",
        ".kobo/kepub/store-book",
        ".kobo-images/cover.parsed",
        ".adds/koreader/koreader.sh",
        ".adds/koreader/settings/statistics.sqlite3",
        "Kerr, Philip/La trilogie berlinoise.kepub.epub",
        "Kerr, Philip/La trilogie berlinoise.sdr/metadata.epub.lua",
    ]:
        assert rel not in files, rel


def test_with_koreader_adds_settings_and_sidecars(tmp_path: Path, make_kobo) -> None:
    files = _selected(make_kobo(tmp_path, populated=True), with_koreader=True)
    assert ".adds/koreader/settings/statistics.sqlite3" in files
    assert "Kerr, Philip/La trilogie berlinoise.sdr/metadata.epub.lua" in files
    assert ".adds/koreader/koreader.sh" not in files


def test_with_books_adds_books_but_not_caches(tmp_path: Path, make_kobo) -> None:
    files = _selected(make_kobo(tmp_path, populated=True), with_books=True)
    assert "Kerr, Philip/La trilogie berlinoise.kepub.epub" in files
    assert ".kobo/kepub/store-book" in files
    assert ".kobo-images/cover.parsed" not in files
    assert ".kobo/dict/dicthtml-fr.zip" not in files
