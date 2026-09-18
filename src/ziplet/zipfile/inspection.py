"""Structured, metadata-only archive inspection results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ziplet.zipfile.extract import ExtractViolation

__all__ = ["InspectionMember", "InspectionResult"]


@dataclass(frozen=True)
class InspectionMember:
    """Metadata and policy findings for one central-directory entry."""

    member: str
    target: Path | None
    is_directory: bool
    compressed_size: int
    uncompressed_size: int
    compression_ratio: float | None
    encrypted: bool
    is_symlink: bool
    is_special_file: bool
    violations: tuple[ExtractViolation, ...] = ()


@dataclass(frozen=True)
class InspectionResult:
    """A side-effect-free report produced from ZIP metadata only."""

    total_entries: int
    total_compressed_size: int
    total_uncompressed_size: int
    members: tuple[InspectionMember, ...]
    duplicate_member_names: tuple[str, ...]
    duplicate_targets: tuple[Path, ...]
    suspicious_paths: tuple[str, ...]
    encrypted_members: tuple[str, ...]
    large_members: tuple[str, ...]
    compress_ratio_outliers: tuple[str, ...]
    symlinks: tuple[str, ...]
    special_files: tuple[str, ...]
    warnings: tuple[ExtractViolation, ...]
    violations: tuple[ExtractViolation, ...]
    member_count_over_limit: bool
