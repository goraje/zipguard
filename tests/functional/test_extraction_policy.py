from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

import ziplet
from ziplet.zipfile.info import ZipInfo


def test_policy_extracts_mixed_archive_with_member_results(tmp_path: Path) -> None:
    archive = tmp_path / "policy.zip"
    destination = tmp_path / "extracted"
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("docs/readme.txt", b"readme")
        zf.writestr("data.bin", b"data")
        zf.writestr("../outside.txt", b"blocked")

    with ziplet.ZipFile(archive) as zf:
        result = zf.extractall(
            destination,
            policy=ziplet.ExtractPolicy(
                max_compression_ratio=None,
                on_violation=ziplet.ViolationAction.SKIP,
            ),
        )

    assert result.extracted_count == 2
    assert result.skipped_count == 1
    assert [member.status for member in result.members] == [
        ziplet.MemberStatus.EXTRACTED,
        ziplet.MemberStatus.EXTRACTED,
        ziplet.MemberStatus.SKIPPED,
    ]
    assert (destination / "docs/readme.txt").read_bytes() == b"readme"
    assert (destination / "data.bin").read_bytes() == b"data"
    assert not (tmp_path / "outside.txt").exists()


def test_policy_preview_is_a_real_dry_run(tmp_path: Path) -> None:
    archive = tmp_path / "preview.zip"
    destination = tmp_path / "preview"
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("file.txt", b"payload")

    with ziplet.ZipFile(archive) as zf:
        result = zf.extractall(
            destination,
            policy=ziplet.ExtractPolicy(
                max_compression_ratio=None,
                preview_only=True,
            ),
        )

    assert result.preview_only
    assert result.extracted_count == 0
    assert result.members[0].status == ziplet.MemberStatus.PREVIEWED
    assert not destination.exists()


def test_runtime_quota_preserves_existing_file(tmp_path: Path) -> None:
    archive = tmp_path / "quota.zip"
    destination = tmp_path / "out"
    destination.mkdir()
    existing = destination / "second.txt"
    existing.write_bytes(b"original")

    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("first.txt", b"1234")
        zf.writestr("second.txt", b"replacement")

    with ziplet.ZipFile(archive) as zf:
        with pytest.warns(
            UserWarning, match="total declared uncompressed size exceeds policy limit"
        ):
            with pytest.raises(ziplet.ExtractionError):
                zf.extractall(
                    destination,
                    policy=ziplet.ExtractPolicy(
                        max_total_uncompressed_size=5,
                        on_violation=ziplet.ViolationAction.WARN,
                        overwrite_policy=ziplet.OverwritePolicy.REPLACE,
                    ),
                )

    assert existing.read_bytes() == b"original"
    assert not list(destination.glob(".ziplet-*"))


def test_allowed_symlink_is_materialized_without_following_it(tmp_path: Path) -> None:
    archive = tmp_path / "symlink.zip"
    destination = tmp_path / "out"
    info = ZipInfo("link")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr(info, b"target.txt")

    with ziplet.ZipFile(archive) as zf:
        result = zf.extractall(
            destination,
            policy=ziplet.ExtractPolicy(
                allow_symlinks=True,
                max_compression_ratio=None,
            ),
        )

    link = destination / "link"
    assert result.extracted_count == 1
    assert link.is_symlink()
    assert os.readlink(link) == "target.txt"


def test_warn_still_rejects_path_escape(tmp_path: Path) -> None:
    archive = tmp_path / "escape.zip"
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("../outside.txt", b"blocked")

    with ziplet.ZipFile(archive) as zf:
        with pytest.raises(ziplet.ExtractionError):
            zf.extractall(
                tmp_path / "out",
                policy=ziplet.ExtractPolicy(
                    on_violation=ziplet.ViolationAction.WARN,
                    max_compression_ratio=None,
                ),
            )


def test_existing_symlink_directory_is_not_followed(tmp_path: Path) -> None:
    archive = tmp_path / "symlink-dir.zip"
    destination = tmp_path / "out"
    outside = tmp_path / "outside"
    destination.mkdir()
    outside.mkdir()
    (destination / "nested").symlink_to(outside, target_is_directory=True)
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("nested/payload.txt", b"blocked")

    with ziplet.ZipFile(archive) as zf:
        with pytest.raises(ziplet.ExtractionError):
            zf.extractall(
                destination,
                policy=ziplet.ExtractPolicy(max_compression_ratio=None),
            )

    assert not (outside / "payload.txt").exists()
