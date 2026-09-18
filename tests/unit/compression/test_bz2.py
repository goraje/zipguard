from __future__ import annotations

import bz2 as _bz2

import pytest

from ziplet.compression import bz2
from ziplet.compression.methods import (
    ZIP_BZIP2,
    CompressionEntry,
    CompressorBase,
    DecompressorBase,
)

pytestmark = pytest.mark.skipif(
    bz2.compression_entry is None,
    reason="bz2 not available",
)

SAMPLE_DATA = b"Hello, bzip2 world! " * 100


def _entry() -> CompressionEntry:
    assert bz2.compression_entry is not None
    return bz2.compression_entry


class TestBz2CompressionEntry:
    def test_entry_is_compression_entry(self) -> None:
        assert isinstance(_entry(), CompressionEntry)

    def test_compression_method_is_zip_bzip2(self) -> None:
        assert _entry().compression_method == ZIP_BZIP2

    def test_compressor_factory_returns_compressor_base(self) -> None:
        compressor = _entry().compressor_factory(None)
        assert isinstance(compressor, CompressorBase)

    def test_decompressor_factory_returns_decompressor_base(self) -> None:
        decompressor = _entry().decompressor_factory()
        assert isinstance(decompressor, DecompressorBase)


class TestBz2Compressor:
    def _make_compressor(self, level: int | None = None) -> CompressorBase:
        compressor = _entry().compressor_factory(level)
        assert compressor is not None
        return compressor

    def test_compress_returns_bytes(self) -> None:
        c = self._make_compressor()
        assert isinstance(c.compress(SAMPLE_DATA), bytes)

    def test_flush_returns_bytes(self) -> None:
        c = self._make_compressor()
        c.compress(SAMPLE_DATA)
        assert isinstance(c.flush(), bytes)

    def test_compress_empty_returns_bytes(self) -> None:
        c = self._make_compressor()
        result = c.compress(b"") + c.flush()
        assert isinstance(result, bytes)

    def test_round_trip_default_level(self) -> None:
        c = self._make_compressor()
        compressed = c.compress(SAMPLE_DATA) + c.flush()
        assert _bz2.decompress(compressed) == SAMPLE_DATA

    def test_round_trip_level_1(self) -> None:
        c = self._make_compressor(level=1)
        compressed = c.compress(SAMPLE_DATA) + c.flush()
        assert _bz2.decompress(compressed) == SAMPLE_DATA

    def test_round_trip_level_9(self) -> None:
        c = self._make_compressor(level=9)
        compressed = c.compress(SAMPLE_DATA) + c.flush()
        assert _bz2.decompress(compressed) == SAMPLE_DATA

    def test_compress_produces_smaller_output_for_repetitive_data(self) -> None:
        c = self._make_compressor()
        compressed = c.compress(SAMPLE_DATA) + c.flush()
        assert len(compressed) < len(SAMPLE_DATA)

    def test_chunked_compress_round_trip(self) -> None:
        chunk_size = 50
        c = self._make_compressor(level=1)
        compressed = b""
        for i in range(0, len(SAMPLE_DATA), chunk_size):
            compressed += c.compress(SAMPLE_DATA[i : i + chunk_size])
        compressed += c.flush()
        assert _bz2.decompress(compressed) == SAMPLE_DATA


class TestBz2Decompressor:
    def _make_decompressor(self) -> DecompressorBase:
        decompressor = _entry().decompressor_factory()
        assert decompressor is not None
        return decompressor

    def _make_compressed(self, data: bytes = SAMPLE_DATA) -> bytes:
        return _bz2.compress(data)

    def test_eof_starts_false(self) -> None:
        d = self._make_decompressor()
        assert d.eof is False

    def test_decompress_returns_bytes(self) -> None:
        d = self._make_decompressor()
        compressed = self._make_compressed()
        result = d.decompress(compressed)
        assert isinstance(result, bytes)

    def test_round_trip(self) -> None:
        d = self._make_decompressor()
        compressed = self._make_compressed()
        assert d.decompress(compressed) == SAMPLE_DATA

    def test_eof_true_after_full_stream(self) -> None:
        d = self._make_decompressor()
        compressed = self._make_compressed()
        d.decompress(compressed)
        assert d.eof is True

    def test_empty_compressed_stream(self) -> None:
        data = b""
        c = _entry().compressor_factory(None)
        assert c is not None
        compressed = c.compress(data) + c.flush()
        d = self._make_decompressor()
        assert d.decompress(compressed) == data

    def test_decompress_respects_max_length(self) -> None:
        data = SAMPLE_DATA * 100
        d = self._make_decompressor()
        compressed = self._make_compressed(data)

        first = d.decompress(compressed, 17)
        assert len(first) <= 17

        output = first
        while not d.eof:
            output += d.decompress(b"", 17)
        assert output == data
