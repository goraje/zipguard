from __future__ import annotations

import struct

import pytest

from ziplet.compression import lzma
from ziplet.compression.methods import (
    ZIP_LZMA,
    CompressionEntry,
    CompressorBase,
    DecompressorBase,
)

pytestmark = pytest.mark.skipif(
    lzma.compression_entry is None,
    reason="lzma not available",
)

SAMPLE_DATA = b"Hello, LZMA world! " * 100


def _entry() -> CompressionEntry:
    assert lzma.compression_entry is not None
    return lzma.compression_entry


class TestLzmaCompressionEntry:
    def test_entry_is_compression_entry(self) -> None:
        assert isinstance(_entry(), CompressionEntry)

    def test_compression_method_is_zip_lzma(self) -> None:
        assert _entry().compression_method == ZIP_LZMA

    def test_compressor_factory_returns_compressor_base(self) -> None:
        compressor = _entry().compressor_factory(None)
        assert isinstance(compressor, CompressorBase)

    def test_compressor_factory_ignores_level(self) -> None:
        c1 = _entry().compressor_factory(None)
        c2 = _entry().compressor_factory(9)
        assert isinstance(c1, CompressorBase)
        assert isinstance(c2, CompressorBase)

    def test_decompressor_factory_returns_decompressor_base(self) -> None:
        decompressor = _entry().decompressor_factory()
        assert isinstance(decompressor, DecompressorBase)


class TestLzmaCompressor:
    def _make_compressor(self) -> CompressorBase:
        compressor = _entry().compressor_factory(None)
        assert compressor is not None
        return compressor

    def test_compress_returns_bytes(self) -> None:
        c = self._make_compressor()
        result = c.compress(SAMPLE_DATA)
        assert isinstance(result, bytes)

    def test_flush_returns_bytes(self) -> None:
        c = self._make_compressor()
        c.compress(SAMPLE_DATA)
        assert isinstance(c.flush(), bytes)

    def test_first_compress_call_prepends_header(self) -> None:
        c = self._make_compressor()
        output = c.compress(b"x")
        # Header: 1 byte version (9), 1 byte flags (4), 2-byte props length LE
        assert len(output) >= 4
        version, flags = output[0], output[1]
        assert version == 9
        assert flags == 4
        (psize,) = struct.unpack("<H", output[2:4])
        assert psize > 0
        assert len(output) >= 4 + psize

    def test_flush_on_fresh_compressor_prepends_header(self) -> None:
        c = self._make_compressor()
        output = c.flush()
        assert len(output) >= 4
        version, flags = output[0], output[1]
        assert version == 9
        assert flags == 4

    def test_subsequent_compress_does_not_repeat_header(self) -> None:
        c = self._make_compressor()
        first = c.compress(b"a")
        (psize,) = struct.unpack("<H", first[2:4])
        second = c.compress(b"b")
        # Second call should not start with the version/props header
        if len(second) >= 1:
            assert not (len(second) >= 4 and second[0] == 9 and second[1] == 4), (
                "header should not repeat on second compress call"
            )

    def test_round_trip(self) -> None:
        c = self._make_compressor()
        compressed = c.compress(SAMPLE_DATA) + c.flush()
        d = _entry().decompressor_factory()
        assert d is not None
        result = d.decompress(compressed)
        assert result == SAMPLE_DATA

    def test_round_trip_empty_data(self) -> None:
        c = self._make_compressor()
        compressed = c.compress(b"") + c.flush()
        d = _entry().decompressor_factory()
        assert d is not None
        result = d.decompress(compressed)
        assert result == b""

    def test_chunked_compress_round_trip(self) -> None:
        chunk_size = 50
        c = self._make_compressor()
        compressed = b""
        for i in range(0, len(SAMPLE_DATA), chunk_size):
            compressed += c.compress(SAMPLE_DATA[i : i + chunk_size])
        compressed += c.flush()
        d = _entry().decompressor_factory()
        assert d is not None
        assert d.decompress(compressed) == SAMPLE_DATA


class TestLzmaDecompressor:
    def _make_decompressor(self) -> DecompressorBase:
        decompressor = _entry().decompressor_factory()
        assert decompressor is not None
        return decompressor

    def _make_compressed(self, data: bytes = SAMPLE_DATA) -> bytes:
        c = _entry().compressor_factory(None)
        assert c is not None
        return c.compress(data) + c.flush()

    def test_eof_starts_false(self) -> None:
        d = self._make_decompressor()
        assert d.eof is False

    def test_decompress_returns_bytes(self) -> None:
        d = self._make_decompressor()
        compressed = self._make_compressed()
        assert isinstance(d.decompress(compressed), bytes)

    def test_round_trip(self) -> None:
        d = self._make_decompressor()
        compressed = self._make_compressed()
        assert d.decompress(compressed) == SAMPLE_DATA

    def test_eof_after_complete_stream(self) -> None:
        d = self._make_decompressor()
        compressed = self._make_compressed()
        d.decompress(compressed)
        assert d.eof is True

    def test_partial_header_returns_empty(self) -> None:
        d = self._make_decompressor()
        # Provide only 2 bytes â€“ not enough for the header length field
        result = d.decompress(b"\x09\x04")
        assert result == b""
        assert d.eof is False

    def test_header_buffer_accumulates_across_calls(self) -> None:
        compressed = self._make_compressed(b"abc")
        d = self._make_decompressor()
        # Feed byte by byte until we have a non-empty result
        output = b""
        for byte in compressed:
            output += d.decompress(bytes([byte]))
        assert output == b"abc"

    def test_chunked_decompress_round_trip(self) -> None:
        compressed = self._make_compressed()
        d = self._make_decompressor()
        chunk_size = 20
        output = b""
        for i in range(0, len(compressed), chunk_size):
            output += d.decompress(compressed[i : i + chunk_size])
        assert output == SAMPLE_DATA

    def test_decompress_respects_max_length(self) -> None:
        data = SAMPLE_DATA * 100
        d = self._make_decompressor()
        compressed = self._make_compressed(data)

        output = b""
        chunk = compressed
        while not d.eof:
            part = d.decompress(chunk, 17)
            assert len(part) <= 17
            output += part
            chunk = b""
        assert output == data
