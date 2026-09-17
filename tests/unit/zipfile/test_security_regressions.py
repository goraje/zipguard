from __future__ import annotations

import struct

import pytest

from ziplet.compression import lzma
from ziplet.exceptions import BadZipFile
from ziplet.zipfile.ext import ZipExtFile
from ziplet.zipfile.file import ZipFileExtra
from ziplet.zipfile.info import ZipInfo


def test_max_n_is_31_bit_maximum() -> None:
    assert ZipExtFile.MAX_N == (1 << 31) - 1


def test_aes_version_override_is_validated() -> None:
    with pytest.raises(ValueError, match="must be 1 or 2"):
        ZipFileExtra(force_wz_aes_version=3)


def test_lzma_oversized_dictionary_is_rejected() -> None:
    if lzma.compression_entry is None:
        pytest.skip("lzma not available")

    props = bytes([0x5D]) + struct.pack("<I", 1 << 31)
    with pytest.raises(BadZipFile, match="dictionary size"):
        lzma._lzma1_filter_from_props(props)


def test_aes_defaults_to_version_two_and_zero_crc() -> None:
    info = ZipInfo("payload.bin")
    info.aes_extra.wz_aes_vendor_id = b"AE"
    info.aes_extra.wz_aes_strength = 3
    info.file_size = 1024
    info.compress_type = 8

    extra, crc, _ = info.encode_extra(0x12345678, info.compress_type)

    _, _, version = struct.unpack("<HHH", extra[:6])
    assert version == 2
    assert crc == 0
