from pathlib import Path

from kobocore.manifest import FileEntry, Manifest, hash_files, sha256_file


def test_sha256_file(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("abc")
    assert sha256_file(f) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_hash_files_records_relative_posix_paths(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("hello")
    [entry] = hash_files(tmp_path, [Path("sub/b.txt")])
    assert entry == FileEntry("sub/b.txt", 5, sha256_file(tmp_path / "sub/b.txt"))


def test_manifest_round_trip(tmp_path: Path) -> None:
    manifest = Manifest(
        serial="N428TEST",
        hardware="libra-colour",
        firmware="4.46.23852",
        db_version=176,
        created_at="2026-11-04T18:30:00+00:00",
        files=[FileEntry("x", 1, "00")],
    )
    path = manifest.write(tmp_path)
    assert path.name == "manifest.json"
    assert Manifest.load(tmp_path) == manifest
    assert manifest.total_size == 1
