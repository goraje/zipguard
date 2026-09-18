"""Functional coverage for the ``zipfile.Path``-style navigation API."""

from __future__ import annotations

from pathlib import Path as FsPath

import ziplet
from ziplet import Path
from ziplet.exceptions import BadZipFile


def _build_project_archive(archive: FsPath) -> None:
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("README.md", "top level readme")
        zf.writestr("src/pkg/__init__.py", "")
        zf.writestr("src/pkg/module.py", "def f():\n    return 1\n")
        zf.writestr("src/pkg/data/values.json", '{"a": 1}')
        zf.writestr("tests/test_module.py", "def test_f():\n    assert True\n")


def test_traverse_read_and_glob_a_nested_archive(tmp_path: FsPath) -> None:
    archive = tmp_path / "project.zip"
    _build_project_archive(archive)

    root = Path(archive)
    assert root.name == archive.name
    assert root.is_dir()

    readme = root / "README.md"
    assert readme.is_file()
    assert readme.read_text(encoding="utf-8") == "top level readme"

    pkg_dir = root / "src" / "pkg"
    assert pkg_dir.is_dir()
    assert {child.name for child in pkg_dir.iterdir()} == {
        "__init__.py",
        "module.py",
        "data",
    }

    module = pkg_dir / "module.py"
    assert module.suffix == ".py"
    assert module.stem == "module"
    assert module.parent == pkg_dir

    all_py_files = {p.at for p in root.rglob("*.py")}
    assert all_py_files == {
        "src/pkg/__init__.py",
        "src/pkg/module.py",
        "tests/test_module.py",
    }

    json_files = list((pkg_dir / "data").glob("*.json"))
    assert len(json_files) == 1
    assert json_files[0].read_bytes() == b'{"a": 1}'


def test_read_aes_encrypted_member_through_path(tmp_path: FsPath) -> None:
    archive = tmp_path / "secure.zip"
    password = b"hunter2-super-secret"
    with ziplet.ZipFile(archive, "w", encryption=ziplet.WZ_AES) as zf:
        zf.setpassword(password)
        zf.writestr("confidential/plan.txt", "launch codes")
        zf.writestr("public/notice.txt", "nothing to see here", encryption=None)

    root = Path(archive)

    # Unencrypted sibling member is readable without a password.
    assert (root / "public" / "notice.txt").read_bytes() == b"nothing to see here"

    # The encrypted member requires the password, matching ZipFile.open().
    encrypted_member = root / "confidential" / "plan.txt"
    with encrypted_member.open("rb", pwd=password) as fh:
        assert fh.read() == b"launch codes"

    # Passing the wrong password surfaces the same error ZipFile.open would.
    import pytest

    with pytest.raises((BadZipFile, RuntimeError, ValueError)):
        with encrypted_member.open("rb", pwd=b"wrong-password") as fh:
            fh.read()


def test_implied_directories_survive_round_trip_without_explicit_entries(
    tmp_path: FsPath,
) -> None:
    archive = tmp_path / "implied.zip"
    # Intentionally omit directory entries; only files are written.
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("a/b/c/leaf.txt", "deep leaf")

    root = Path(archive)
    a = root / "a"
    b = a / "b"
    c = b / "c"
    assert a.is_dir()
    assert b.is_dir()
    assert c.is_dir()
    assert [child.name for child in c.iterdir()] == ["leaf.txt"]
    assert (c / "leaf.txt").read_text(encoding="utf-8") == "deep leaf"


def test_open_existing_zipfile_object_reuses_password(tmp_path: FsPath) -> None:
    archive = tmp_path / "reuse.zip"
    password = b"zip-crypto-secret"
    with ziplet.ZipFile(archive, "w", encryption=ziplet.ZIP_CRYPTO) as zf:
        zf.setpassword(password)
        zf.writestr("data/secret.bin", b"\x01\x02\x03")

    zf = ziplet.ZipFile(archive)
    zf.setpassword(password)
    path = Path(zf)
    try:
        assert (path / "data" / "secret.bin").read_bytes() == b"\x01\x02\x03"
    finally:
        zf.close()


def test_missing_path_is_not_a_symlink(tmp_path: FsPath) -> None:
    archive = tmp_path / "missing.zip"
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("present.txt", b"payload")
    assert not (Path(archive) / "missing.txt").is_symlink()
