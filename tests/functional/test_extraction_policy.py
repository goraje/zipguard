from __future__ import annotations

from pathlib import Path

import ziplet


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
