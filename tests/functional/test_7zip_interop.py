"""Functional tests â€” ziplet â†” 7-Zip interoperability.

All tests are skipped automatically when 7-Zip is not installed at its default
Windows location.  Only AES-256 encryption is exercised here; other encryption
modes are covered by the smoke-test suite.

Direction A: ziplet writes a ZIP â†’ 7-Zip validates / extracts it.
Direction B: 7-Zip writes a ZIP â†’ ziplet reads it.
Additional:  edge-case functional scenarios that span both sides.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import ziplet
from ziplet import ZipFile, ZipFileExtra

# ---------------------------------------------------------------------------
# 7-Zip location + module-level skip
# ---------------------------------------------------------------------------

SZ_EXE = Path("7z")

pytestmark = [
    pytest.mark.windows,
    pytest.mark.skipif(
        sys.platform != "win32",
        reason="7-Zip interoperability tests run on Windows only",
    ),
    pytest.mark.skipif(
        not shutil.which(SZ_EXE),
        reason="7-Zip not found in PATH; required for interoperability tests",
    ),
]

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

PASSWORD = b"Cefzuj-hetveg-xifve5"
_PWD_STR = PASSWORD.decode()

# Small payload used when compression method does not matter
CONTENT = b"Hello from ziplet functional tests."

# Larger, compressible payload used to ensure 7z actually applies Deflate
# (7z silently falls back to Store for tiny files even when -mm=Deflate is passed)
LARGE_CONTENT = b"abcdefghij" * 1024  # 10 240 bytes


# ---------------------------------------------------------------------------
# 7z helpers
# ---------------------------------------------------------------------------


def _sz(*args: str) -> subprocess.CompletedProcess[str]:
    """Run 7-Zip with *args* and return the CompletedProcess."""
    return subprocess.run(
        [str(SZ_EXE), *args],
        capture_output=True,
        text=True,
    )


def _sz_test(archive: Path, pwd: str | None = None) -> int:
    """Run '7z t' on *archive* and return the exit code."""
    args = ["t"]
    if pwd is not None:
        args.append(f"-p{pwd}")
    args.append(str(archive))
    return _sz(*args).returncode


def _sz_list_metadata(archive: Path) -> str:
    """Return the stdout of '7z l -slt' for *archive* (no password needed)."""
    return _sz("l", "-slt", str(archive)).stdout


def _sz_create_encrypted(
    archive: Path,
    content: bytes,
    filename: str,
    method: str = "AES256",
    compression: str | None = None,
    tmp: Path | None = None,
) -> None:
    """Create a single-entry encrypted ZIP using 7-Zip.

    Stages *content* as *filename* inside *tmp* (defaults to the archive's
    parent directory) so that 7-Zip stores only the basename in the archive.
    """
    stage_dir = tmp or archive.parent
    source = stage_dir / filename
    source.write_bytes(content)

    args = ["a", "-tzip"]
    if compression:
        args.append(f"-mm={compression}")
    args += [f"-mem={method}", f"-p{_PWD_STR}", str(archive), str(source)]

    result = _sz(*args)
    assert result.returncode == 0, (
        f"7z failed to create archive:\n{result.stdout}\n{result.stderr}"
    )


# ===========================================================================
# Direction A: ziplet writes â†’ 7-Zip validates / extracts
# ===========================================================================


class TestPyWrites7zValidates:
    """ziplet creates archives; 7-Zip must accept them."""

    def test_aes256_stored(self, tmp_path: Path) -> None:
        zp = tmp_path / "a1.zip"
        with ZipFile(zp, "w", encryption=ziplet.WZ_AES) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("file.txt", CONTENT)
        assert _sz_test(zp, _PWD_STR) == 0

    def test_aes256_deflated(self, tmp_path: Path) -> None:
        zp = tmp_path / "a2.zip"
        with ZipFile(
            zp,
            "w",
            compression=ziplet.ZIP_DEFLATED,
            encryption=ziplet.WZ_AES,
        ) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("file.txt", LARGE_CONTENT)
        assert _sz_test(zp, _PWD_STR) == 0

    def test_aes256_bzip2(self, tmp_path: Path) -> None:
        zp = tmp_path / "a3.zip"
        with ZipFile(
            zp, "w", compression=ziplet.ZIP_BZIP2, encryption=ziplet.WZ_AES
        ) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("file.txt", LARGE_CONTENT)
        assert _sz_test(zp, _PWD_STR) == 0

    def test_aes256_lzma(self, tmp_path: Path) -> None:
        zp = tmp_path / "a4.zip"
        with ZipFile(
            zp, "w", compression=ziplet.ZIP_LZMA, encryption=ziplet.WZ_AES
        ) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("file.txt", LARGE_CONTENT)
        assert _sz_test(zp, _PWD_STR) == 0

    def test_aes256_multi_file(self, tmp_path: Path) -> None:
        zp = tmp_path / "a5.zip"
        with ZipFile(zp, "w", encryption=ziplet.WZ_AES) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("alpha.txt", b"alpha content")
            zf.writestr("beta.txt", b"beta content")
            zf.writestr("gamma.txt", b"gamma content")
        assert _sz_test(zp, _PWD_STR) == 0

    def test_aes256_7z_extracts_correct_content(self, tmp_path: Path) -> None:
        """7-Zip must be able to extract the exact bytes written by ziplet."""
        zp = tmp_path / "a6.zip"
        with ZipFile(zp, "w", encryption=ziplet.WZ_AES) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("payload.txt", CONTENT)

        out_dir = tmp_path / "extracted"
        out_dir.mkdir()
        result = _sz("e", f"-p{_PWD_STR}", f"-o{out_dir}", "-y", str(zp))
        assert result.returncode == 0, result.stderr
        assert (out_dir / "payload.txt").read_bytes() == CONTENT

    def test_aes256_force_v1_recognised_by_7z(self, tmp_path: Path) -> None:
        """force_wz_aes_version=1 â†’ 7-Zip lists AES-256 and passes integrity check."""
        zp = tmp_path / "a7.zip"
        x = ZipFileExtra(force_wz_aes_version=1)
        with ZipFile(zp, "w", encryption=ziplet.WZ_AES, extra=x) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("f.txt", CONTENT * 5)
        meta = _sz_list_metadata(zp)
        assert "AES-256" in meta
        assert _sz_test(zp, _PWD_STR) == 0

    def test_aes256_force_v2_recognised_by_7z(self, tmp_path: Path) -> None:
        """force_wz_aes_version=2 (zero-CRC) â†’ 7-Zip lists AES-256 and passes."""
        zp = tmp_path / "a8.zip"
        x = ZipFileExtra(force_wz_aes_version=2)
        with ZipFile(zp, "w", encryption=ziplet.WZ_AES, extra=x) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("f.txt", CONTENT * 10)
        meta = _sz_list_metadata(zp)
        assert "AES-256" in meta
        assert _sz_test(zp, _PWD_STR) == 0

    def test_no_encryption_baseline(self, tmp_path: Path) -> None:
        """Unencrypted archive written by ziplet passes 7-Zip integrity check."""
        zp = tmp_path / "a9.zip"
        with ZipFile(zp, "w") as zf:
            zf.writestr("f.txt", CONTENT)
        assert _sz_test(zp) == 0


# ===========================================================================
# Direction B: 7-Zip writes â†’ ziplet reads
# ===========================================================================


class TestSevenZWritesPyReads:
    """7-Zip creates archives; ziplet must read them correctly."""

    def test_7z_aes256_stored(self, tmp_path: Path) -> None:
        zp = tmp_path / "b1.zip"
        _sz_create_encrypted(zp, CONTENT, "hello.txt", tmp=tmp_path)
        with ZipFile(zp, "r") as zf:
            zf.setpassword(PASSWORD)
            assert zf.read("hello.txt") == CONTENT

    def test_7z_aes256_deflate(self, tmp_path: Path) -> None:
        """7-Zip writes AES-256 + Deflate; ziplet decompresses correctly."""
        zp = tmp_path / "b2.zip"
        _sz_create_encrypted(
            zp, LARGE_CONTENT, "large.txt", compression="Deflate", tmp=tmp_path
        )
        with ZipFile(zp, "r") as zf:
            zf.setpassword(PASSWORD)
            assert zf.read("large.txt") == LARGE_CONTENT

    def test_7z_zipcrypto(self, tmp_path: Path) -> None:
        """7-Zip writes ZipCrypto; ziplet auto-detects and decrypts."""
        zp = tmp_path / "b3.zip"
        _sz_create_encrypted(
            zp, CONTENT, "secret.txt", method="ZipCrypto", tmp=tmp_path
        )
        with ZipFile(zp, "r") as zf:
            zf.setpassword(PASSWORD)
            assert zf.read("secret.txt") == CONTENT

    def test_7z_aes256_multi_file(self, tmp_path: Path) -> None:
        """7-Zip writes a multi-entry AES-256 archive; all entries readable."""
        expected = {
            "m1.txt": b"first file contents",
            "m2.txt": b"second file contents",
            "m3.txt": b"third file contents",
        }
        for name, data in expected.items():
            (tmp_path / name).write_bytes(data)

        result = _sz(
            "a",
            "-tzip",
            "-mem=AES256",
            f"-p{_PWD_STR}",
            str(tmp_path / "b4.zip"),
            *[str(tmp_path / n) for n in expected],
        )
        assert result.returncode == 0, result.stderr

        with ZipFile(tmp_path / "b4.zip", "r") as zf:
            zf.setpassword(PASSWORD)
            for name, data in expected.items():
                assert zf.read(name) == data

    def test_7z_no_encryption(self, tmp_path: Path) -> None:
        """7-Zip writes a plain (unencrypted) ZIP; ziplet reads it."""
        zp = tmp_path / "b5.zip"
        (tmp_path / "plain.txt").write_bytes(CONTENT)
        result = _sz("a", "-tzip", str(zp), str(tmp_path / "plain.txt"))
        assert result.returncode == 0
        with ZipFile(zp, "r") as zf:
            assert zf.read("plain.txt") == CONTENT


# ===========================================================================
# Additional functional tests
# ===========================================================================


class TestAdditional:
    def test_wrong_password_on_7z_archive_raises(self, tmp_path: Path) -> None:
        """ziplet raises RuntimeError when given the wrong password."""
        zp = tmp_path / "f1.zip"
        _sz_create_encrypted(zp, CONTENT, "secret.txt", tmp=tmp_path)
        with ZipFile(zp, "r") as zf:
            zf.setpassword(b"completely-wrong-password")
            with pytest.raises(RuntimeError):
                zf.read("secret.txt")

    def test_testzip_on_7z_written_archive(self, tmp_path: Path) -> None:
        """testzip() returns None (no corrupt entries) for a 7-Zip-written archive."""
        zp = tmp_path / "f2.zip"
        _sz_create_encrypted(zp, CONTENT, "file.txt", tmp=tmp_path)
        with ZipFile(zp, "r") as zf:
            zf.setpassword(PASSWORD)
            assert zf.testzip() is None

    def test_binary_content_round_trip_sha256(self, tmp_path: Path) -> None:
        """64 KiB of binary data: ziplet writes â†’ 7z verifies â†’ py re-reads.

        SHA-256 of recovered data must equal SHA-256 of original.
        """
        # Deterministic pseudo-random payload (repeating 0-255 pattern Ă— 256)
        binary = bytes(bytearray(range(256)) * 256)  # 65 536 bytes
        expected_digest = hashlib.sha256(binary).hexdigest()

        zp = tmp_path / "f3.zip"
        with ZipFile(zp, "w", encryption=ziplet.WZ_AES) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("binary.bin", binary)

        assert _sz_test(zp, _PWD_STR) == 0

        with ZipFile(zp, "r") as zf:
            zf.setpassword(PASSWORD)
            recovered = zf.read("binary.bin")

        assert hashlib.sha256(recovered).hexdigest() == expected_digest

    def test_unicode_filename_has_utf8_flag(self, tmp_path: Path) -> None:
        """Non-ASCII filenames written by ziplet have the UTF-8 flag set.

        7-Zip's detailed listing (l -slt) should report 'UTF8' in the
        Characteristics field.
        """
        zp = tmp_path / "f4.zip"
        with ZipFile(zp, "w", encryption=ziplet.WZ_AES) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("hĂ©llo_wĂ¶rld.txt", CONTENT)

        meta = _sz_list_metadata(zp)
        assert "UTF8" in meta

    def test_empty_file_entry(self, tmp_path: Path) -> None:
        """A zero-byte entry with AES-256 must pass 7-Zip's integrity check."""
        zp = tmp_path / "f5.zip"
        with ZipFile(zp, "w", encryption=ziplet.WZ_AES) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("empty.txt", b"")
        assert _sz_test(zp, _PWD_STR) == 0

    def test_multi_file_nested_paths_extract_with_7z(self, tmp_path: Path) -> None:
        """Nested archive paths are preserved when 7-Zip extracts the archive."""
        zp = tmp_path / "f6.zip"
        expected = {
            "nested/alpha.txt": b"alpha",
            "nested/deep/beta.bin": b"beta-bytes",
            "root.txt": b"root-data",
        }
        with ZipFile(zp, "w", encryption=ziplet.WZ_AES) as zf:
            zf.setpassword(PASSWORD)
            for name, data in expected.items():
                zf.writestr(name, data)

        out_dir = tmp_path / "nested_extract"
        out_dir.mkdir()
        result = _sz("x", f"-p{_PWD_STR}", f"-o{out_dir}", "-y", str(zp))
        assert result.returncode == 0, result.stderr

        for name, data in expected.items():
            assert (out_dir / Path(name)).read_bytes() == data

    def test_multi_file_with_zero_byte_entry(self, tmp_path: Path) -> None:
        """A mixed archive with an empty file remains valid for both tools."""
        zp = tmp_path / "f7.zip"
        with ZipFile(zp, "w", encryption=ziplet.WZ_AES) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("payload.bin", b"payload")
            zf.writestr("empty.dat", b"")

        assert _sz_test(zp, _PWD_STR) == 0
        with ZipFile(zp, "r") as zf:
            zf.setpassword(PASSWORD)
            assert zf.read("payload.bin") == b"payload"
            assert zf.read("empty.dat") == b""

    def test_multi_file_mixed_compression(self, tmp_path: Path) -> None:
        """Per-entry compression methods can be mixed in one archive."""
        zp = tmp_path / "f8.zip"
        methods = {
            "stored.txt": ziplet.ZIP_STORED,
            "deflated.txt": ziplet.ZIP_DEFLATED,
            "bzip2.txt": ziplet.ZIP_BZIP2,
            "lzma.txt": ziplet.ZIP_LZMA,
        }
        payload = b"compressible-payload-" * 256

        with ZipFile(zp, "w", encryption=ziplet.WZ_AES) as zf:
            zf.setpassword(PASSWORD)
            for name, method in methods.items():
                zf.writestr(name, payload, compress_type=method)

        assert _sz_test(zp, _PWD_STR) == 0
        with ZipFile(zp, "r") as zf:
            zf.setpassword(PASSWORD)
            for name, method in methods.items():
                assert zf.read(name) == payload
                assert zf.getinfo(name).compress_type == method
