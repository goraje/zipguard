"""Opt-in extraction policies and structured extraction results."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ziplet.zipfile.info import ZipInfo

__all__ = [
    "ExtractMemberResult",
    "ExtractPolicy",
    "ExtractResult",
    "ExtractViolation",
    "ExtractionError",
    "MemberStatus",
    "OverwritePolicy",
    "ViolationAction",
]


class OverwritePolicy(str, Enum):
    ERROR = "error"
    SKIP = "skip"
    REPLACE = "replace"
    RENAME = "rename"


class ViolationAction(str, Enum):
    ERROR = "error"
    WARN = "warn"
    SKIP = "skip"


class MemberStatus(str, Enum):
    EXTRACTED = "extracted"
    SKIPPED = "skipped"
    FAILED = "failed"
    PREVIEWED = "previewed"


@dataclass(frozen=True)
class ExtractPolicy:
    destination_root: Path | None = None
    allow_absolute_paths: bool = False
    allow_parent_traversal: bool = False
    allow_windows_drive_paths: bool = False
    allow_symlinks: bool = False
    allow_special_files: bool = False
    allow_overwrite: bool = False
    overwrite_policy: OverwritePolicy = OverwritePolicy.ERROR
    max_member_size: int | None = 256 * 1024 * 1024
    max_total_uncompressed_size: int | None = 1 * 1024 * 1024 * 1024
    max_entries: int | None = 10_000
    max_compression_ratio: float | None = 100.0
    allowed_extensions: frozenset[str] | None = None
    blocked_extensions: frozenset[str] | None = None
    require_utf8_names: bool = True
    reject_duplicate_targets: bool = True
    on_violation: ViolationAction = ViolationAction.ERROR
    check_mtime: bool = False
    check_owner: bool = False
    preview_only: bool = False
    custom_validator: Callable[["ZipInfo", Path], None] | None = None


@dataclass(frozen=True)
class ExtractViolation:
    member: str
    code: str
    message: str
    action: ViolationAction
    target: Path | None = None


@dataclass(frozen=True)
class ExtractMemberResult:
    member: str
    status: MemberStatus
    target: Path | None
    is_directory: bool
    compressed_size: int
    uncompressed_size: int
    compression_ratio: float | None
    bytes_written: int
    violations: tuple[ExtractViolation, ...] = ()
    overwritten: bool = False


@dataclass(frozen=True)
class ExtractResult:
    destination: Path
    members: tuple[ExtractMemberResult, ...]
    violations: tuple[ExtractViolation, ...]
    extracted_count: int
    skipped_count: int
    failed_count: int
    bytes_written: int
    preview_only: bool


class ExtractionError(Exception):
    """Raised after a policy-enabled extraction encounters error violations."""

    def __init__(self, result: ExtractResult) -> None:
        self.result = result
        super().__init__(f"Extraction failed for {result.failed_count} member(s)")


def normalized_destination(path: str | os.PathLike[str]) -> Path:
    return Path(os.path.abspath(os.fspath(path)))
