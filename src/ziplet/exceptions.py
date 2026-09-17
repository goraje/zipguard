from __future__ import annotations

__all__ = ["BadZipFile", "LargeZipFile"]


class BadZipFile(Exception):
    pass


class LargeZipFile(Exception):
    """Raised when writing a zipfile that requires ZIP64 extensions
    and they are disabled."""
