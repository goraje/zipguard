from __future__ import annotations

from ziplet.compression.methods import (
    ZIP_STORED,
    CompressionEntry,
)

compression_entry: CompressionEntry = CompressionEntry(
    compression_method=ZIP_STORED,
    compressor_factory=lambda _level: None,
    decompressor_factory=lambda: None,
)
