from __future__ import annotations

import sys
import zlib

import pytest

from ziplet.compression import deflate
from ziplet.compression.methods import (
    ZIP_DEFLATED,
    CompressionEntry,
    CompressorBase,
    StreamingDecompressor,
)

pytestmark = pytest.mark.skipif(
    deflate.compression_entry is None,
    reason="zlib not available",
)

SAMPLE_DATA = b"Hello, World! " * 100


def _entry() -> CompressionEntry:
    assert deflate.compression_entry is not None
    return deflate.compression_entry


class TestDeflateCompressionEntry:
    def test_entry_is_compression_entry(self) -> None:
        assert isinstance(_entry(), CompressionEntry)

    def test_compression_method_is_zip_deflated(self) -> None:
        assert _entry().compression_method == ZIP_DEFLATED

    def test_compressor_factory_returns_compressor_base(self) -> None:
        compressor = _entry().compressor_factory(None)
        assert isinstance(compressor, CompressorBase)

    def test_decompressor_factory_returns_streaming_decompressor(self) -> None:
        decompressor = _entry().decompressor_factory()
        assert isinstance(decompressor, StreamingDecompressor)


class TestZlibCompressor:
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

    def test_compress_empty_input(self) -> None:
        c = self._make_compressor()
        result = c.compress(b"") + c.flush()
        assert isinstance(result, bytes)

    def test_round_trip_default_level(self) -> None:
        c = self._make_compressor()
        compressed = c.compress(SAMPLE_DATA) + c.flush()
        assert zlib.decompress(compressed, -15) == SAMPLE_DATA

    def test_round_trip_level_1(self) -> None:
        c = self._make_compressor(level=1)
        compressed = c.compress(SAMPLE_DATA) + c.flush()
        assert zlib.decompress(compressed, -15) == SAMPLE_DATA

    def test_round_trip_level_9(self) -> None:
        c = self._make_compressor(level=9)
        compressed = c.compress(SAMPLE_DATA) + c.flush()
        assert zlib.decompress(compressed, -15) == SAMPLE_DATA

    def test_compress_produces_smaller_output_for_repetitive_data(self) -> None:
        c = self._make_compressor()
        compressed = c.compress(SAMPLE_DATA) + c.flush()
        assert len(compressed) < len(SAMPLE_DATA)

    def test_chunked_compress_produces_same_result(self) -> None:
        chunk_size = 50
        c1 = self._make_compressor(level=1)
        c2 = self._make_compressor(level=1)

        single_pass = c1.compress(SAMPLE_DATA) + c1.flush()

        chunked = b""
        for i in range(0, len(SAMPLE_DATA), chunk_size):
            chunked += c2.compress(SAMPLE_DATA[i : i + chunk_size])
        chunked += c2.flush()

        assert zlib.decompress(single_pass, -15) == zlib.decompress(chunked, -15)


class TestZlibDecompressor:
    def _make_decompressor(self) -> StreamingDecompressor:
        decompressor = _entry().decompressor_factory()
        assert isinstance(decompressor, StreamingDecompressor)
        return decompressor

    def _make_compressed(self, data: bytes = SAMPLE_DATA) -> bytes:
        if sys.version_info >= (3, 11):
            return zlib.compress(data, wbits=-15)
        c = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -15)
        return c.compress(data) + c.flush()

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

    def test_flush_returns_bytes(self) -> None:
        d = self._make_decompressor()
        compressed = self._make_compressed()
        d.decompress(compressed)
        assert isinstance(d.flush(), bytes)

    def test_unconsumed_tail_initially_empty(self) -> None:
        d = self._make_decompressor()
        assert d.unconsumed_tail == b""

    def test_decompress_max_length(self) -> None:
        d = self._make_decompressor()
        compressed = self._make_compressed()
        partial = d.decompress(compressed, max_length=10)
        assert isinstance(partial, bytes)
        assert len(partial) <= 10

    def test_decompress_unlimited_with_negative_max_length(self) -> None:
        d = self._make_decompressor()
        compressed = self._make_compressed()
        result = d.decompress(compressed, max_length=-1)
        assert result == SAMPLE_DATA

    def test_chunked_decompress_round_trip(self) -> None:
        compressed = self._make_compressed()
        d = self._make_decompressor()
        chunk_size = 20
        output = b""
        for i in range(0, len(compressed), chunk_size):
            output += d.decompress(compressed[i : i + chunk_size])
        output += d.flush()
        assert output == SAMPLE_DATA

    def test_empty_data_decompress(self) -> None:
        d = self._make_decompressor()
        result = d.decompress(b"")
        assert isinstance(result, bytes)
