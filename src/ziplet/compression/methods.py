from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

__all__ = [
    "BZIP2_VERSION",
    "LZMA_VERSION",
    "ZSTANDARD_VERSION",
    "ZIP_STORED",
    "ZIP_DEFLATED",
    "ZIP_BZIP2",
    "ZIP_LZMA",
    "ZIP_ZSTANDARD",
    "CompressorBase",
    "DecompressorBase",
    "StreamingDecompressor",
    "CompressionEntry",
]

# ---------------------------------------------------------------------------
# ZIP compression method IDs
# ---------------------------------------------------------------------------
ZIP_STORED = 0
ZIP_DEFLATED = 8
ZIP_BZIP2 = 12
ZIP_LZMA = 14
ZIP_ZSTANDARD = 93

# ---------------------------------------------------------------------------
# Minimum ZIP version-needed-to-extract for each compression method
# ---------------------------------------------------------------------------
BZIP2_VERSION = 46
LZMA_VERSION = 63
ZSTANDARD_VERSION = 63


class CompressorBase(ABC):
    """Abstract base class for all compressors."""

    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Compresses a chunk of data.

        Args:
            data: The raw bytes to compress.

        Returns:
            Compressed bytes. May be empty if data is buffered internally.
        """
        ...

    @abstractmethod
    def flush(self) -> bytes:
        """Flushes any remaining buffered data and finalizes the stream.

        Returns:
            The remaining compressed bytes.
        """
        ...


class DecompressorBase(ABC):
    """Abstract base class defining the minimal interface for all decompressors."""

    @property
    @abstractmethod
    def eof(self) -> bool:
        """Whether the end of the compressed stream has been reached.

        Returns:
            True if the decompressor has reached the end of stream,
            False otherwise.
        """
        ...

    @abstractmethod
    def decompress(self, data: bytes, max_length: int = -1) -> bytes:
        """Decompresses a chunk of data.

        Args:
            data: The compressed bytes to decompress.
            max_length: Maximum output size, or ``-1`` for no limit.

        Returns:
            Decompressed bytes.
        """
        ...


class StreamingDecompressor(DecompressorBase):
    """Extended interface for stream-oriented decompressors.

    Extends DecompressorBase with support for bounded decompression,
    leftover tail data, and explicit flushing. Used by decompressors such
    as the zlib/deflate implementation.
    """

    @property
    @abstractmethod
    def unconsumed_tail(self) -> bytes:
        """Data that was not consumed during the last decompress call.

        Returns:
            Bytes that were passed to decompress but not yet processed
            due to a max_length limit.
        """
        ...

    @abstractmethod
    def flush(self) -> bytes:
        """Flushes any remaining buffered data.

        Returns:
            Any remaining decompressed bytes.
        """
        ...

    @abstractmethod
    def decompress(self, data: bytes, max_length: int = -1) -> bytes:
        """Decompresses a chunk of data.

        Args:
            data: The compressed bytes to decompress.
            max_length: Maximum number of bytes to return. If negative,
                there is no limit on the output size.

        Returns:
            Decompressed bytes, up to max_length bytes if specified.
        """
        ...

    @property
    def needs_input(self) -> bool:
        """Whether the decompressor needs more compressed input.

        Custom decompressors that do not buffer output retain the historical
        behavior by using the default value.
        """
        return True


@dataclass(frozen=True)
class CompressionEntry:
    """Registry entry pairing a compressor and decompressor factory for a ZIP method.

    Attributes:
        compression_method: The ZIP compression method ID this entry handles.
        compressor_factory: Callable that accepts an optional compression level
            and returns a CompressorBase instance, or None.
        decompressor_factory: Callable that takes no arguments and returns a
            DecompressorBase instance, or None.
    """

    compression_method: int
    compressor_factory: Callable[[int | None], CompressorBase | None]
    decompressor_factory: Callable[[], DecompressorBase | None]
