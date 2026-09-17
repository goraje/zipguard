from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest import mock

import pytest

import ziplet
from ziplet import ZipFile
from ziplet.compression import registry as _comp_registry
from ziplet.zipfile.shared import MASK_COMPRESSED_PATCH, MASK_STRONG_ENCRYPTION

PASSWORD = b"Cefzuj-hetveg-xifve5"
_TOTALLY_UNKNOWN = 999


class TestZipFileOpenGuards:
    def test_open_while_write_handle_open_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "busy.zip"
        with ZipFile(path, "w") as zf:
            zf.writestr("existing.txt", b"ok")

        with ZipFile(path, "a") as zf:
            writer = zf.open("new.txt", "w")
            try:
                with pytest.raises(ValueError, match="open writing handle"):
                    zf.open("existing.txt", "r")
            finally:
                writer.close()

    def test_second_write_handle_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "two-writers.zip"
        with ZipFile(path, "w") as zf:
            writer = zf.open("a.txt", "w")
            try:
                with pytest.raises(ValueError, match="another write handle"):
                    zf.open("b.txt", "w")
            finally:
                writer.close()


class TestZipFileOpenReadBranches:
    def test_open_with_non_bytes_pwd_argument_raises_type_error(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "enc.zip"
        with ZipFile(path, "w", encryption=ziplet.WZ_AES) as zf:
            zf.setpassword(PASSWORD)
            zf.writestr("secret.txt", b"data")

        with ZipFile(path, "r") as zf:
            with pytest.raises(TypeError, match="pwd: expected bytes, got str"):
                zf.open("secret.txt", pwd=cast(Any, "not-bytes"))

    @pytest.mark.parametrize(
        ("flag", "msg"),
        [
            (MASK_COMPRESSED_PATCH, "compressed patched data"),
            (MASK_STRONG_ENCRYPTION, "strong encryption"),
        ],
    )
    def test_open_with_unsupported_flag_raises(
        self,
        tmp_path: Path,
        flag: int,
        msg: str,
    ) -> None:
        path = tmp_path / "flags.zip"
        with ZipFile(path, "w") as zf:
            zf.writestr("f.txt", b"payload")

        with ZipFile(path, "r") as zf:
            info = zf.getinfo("f.txt")
            info.flag_bits |= flag
            with pytest.raises(NotImplementedError, match=msg):
                zf.open(info)


class TestZipFileExtractSanitization:
    def test_extract_sanitizes_parent_path_segments(self, tmp_path: Path) -> None:
        path = tmp_path / "paths.zip"
        out = tmp_path / "out"

        with ZipFile(path, "w") as zf:
            zf.writestr("../escape.txt", b"safe")

        with ZipFile(path, "r") as zf:
            extracted = Path(zf.extract("../escape.txt", out))

        assert extracted == out / "escape.txt"
        assert extracted.exists()
        assert not (tmp_path / "escape.txt").exists()

    def test_extract_raises_for_empty_sanitized_filename(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.zip"
        out = tmp_path / "out"

        with ZipFile(path, "w") as zf:
            zf.writestr("../.", b"payload")

        with ZipFile(path, "r") as zf:
            with pytest.raises(ValueError, match="Empty filename"):
                zf.extract("../.", out)


class TestZipFileCompressionValidation:
    def test_unknown_compression_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.zip"
        with pytest.raises((NotImplementedError, RuntimeError)):
            with ZipFile(path, "w", compression=_TOTALLY_UNKNOWN) as zf:
                zf.writestr("f.txt", "data")

    @pytest.mark.parametrize(
        ("method", "module_name"),
        [
            (ziplet.ZIP_DEFLATED, "zlib"),
            (ziplet.ZIP_BZIP2, "bz2"),
            (ziplet.ZIP_LZMA, "lzma"),
        ],
    )
    def test_patched_method_unavailable_raises_runtime_error(
        self,
        tmp_path: Path,
        method: int,
        module_name: str,
    ) -> None:
        path = tmp_path / "patched.zip"
        with mock.patch.dict(_comp_registry._registry, clear=False) as patched:
            patched.pop(method, None)
            with pytest.raises(RuntimeError, match=module_name):
                with ZipFile(path, "w", compression=method) as zf:
                    zf.writestr("f.txt", "data")
