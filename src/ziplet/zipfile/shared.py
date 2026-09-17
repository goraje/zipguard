import struct

__all__ = [
    "DEFAULT_VERSION",
    "ZIP64_VERSION",
    "MAX_EXTRACT_VERSION",
    "structEndArchive",
    "stringEndArchive",
    "sizeEndCentDir",
    "structCentralDir",
    "stringCentralDir",
    "sizeCentralDir",
    "structFileHeader",
    "stringFileHeader",
    "sizeFileHeader",
    "structEndArchive64Locator",
    "stringEndArchive64Locator",
    "sizeEndCentDir64Locator",
    "structEndArchive64",
    "stringEndArchive64",
    "sizeEndCentDir64",
    "ZIP64_LIMIT",
    "ZIP_FILECOUNT_LIMIT",
    "ZIP_MAX_COMMENT",
    "MASK_ENCRYPTED",
    "MASK_COMPRESS_OPTION_1",
    "MASK_COMPRESSED_PATCH",
    "MASK_STRONG_ENCRYPTION",
    "MASK_UTF_FILENAME",
    "MASK_USE_DATA_DESCRIPTOR",
]

# ---------------------------------------------------------------------------
# Version constants
# ---------------------------------------------------------------------------
DEFAULT_VERSION = 20
ZIP64_VERSION = 45
MAX_EXTRACT_VERSION = 63

# ---------------------------------------------------------------------------
# Struct formats, magic strings and sizes
# ---------------------------------------------------------------------------

# End of central directory
structEndArchive = b"<4s4H2LH"
stringEndArchive = b"PK\005\006"
sizeEndCentDir = struct.calcsize(structEndArchive)

# Central directory
structCentralDir = "<4s4B4HL2L5H2L"
stringCentralDir = b"PK\001\002"
sizeCentralDir = struct.calcsize(structCentralDir)

# Local file header
structFileHeader = "<4s2B4HL2L2H"
stringFileHeader = b"PK\003\004"
sizeFileHeader = struct.calcsize(structFileHeader)

# Zip64 end-of-central-directory locator
structEndArchive64Locator = "<4sLQL"
stringEndArchive64Locator = b"PK\x06\x07"
sizeEndCentDir64Locator = struct.calcsize(structEndArchive64Locator)

# Zip64 end-of-central-directory record
structEndArchive64 = "<4sQ2H2L4Q"
stringEndArchive64 = b"PK\x06\x06"
sizeEndCentDir64 = struct.calcsize(structEndArchive64)

# ---------------------------------------------------------------------------
# Size limits
# ---------------------------------------------------------------------------
ZIP64_LIMIT = (1 << 31) - 1
ZIP_FILECOUNT_LIMIT = (1 << 16) - 1
ZIP_MAX_COMMENT = (1 << 16) - 1

# ---------------------------------------------------------------------------
# General purpose bit flags
# ---------------------------------------------------------------------------
MASK_ENCRYPTED = 1 << 0
MASK_COMPRESS_OPTION_1 = 1 << 1
MASK_COMPRESSED_PATCH = 1 << 5
MASK_STRONG_ENCRYPTION = 1 << 6
MASK_UTF_FILENAME = 1 << 11
MASK_USE_DATA_DESCRIPTOR = 1 << 3
