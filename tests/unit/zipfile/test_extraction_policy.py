from __future__ import annotations

import io
from pathlib import Path

import pytest

import ziplet
from ziplet.zipfile.extract import ExtractionError


def test_policy_returns_structured_result_and_is_opt_in(tmp_path: Path) -> None:
    archive = tmp_path / "extract.zip"
    output = tmp_path / "out"
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("safe.txt", b"safe")
        zf.writestr("../escape.txt", b"blocked")

    with ziplet.ZipFile(archive) as zf:
        assert isinstance(zf.extract("safe.txt", output), str)
        result = zf.extractall(
            output / "policy",
            policy=ziplet.ExtractPolicy(
                max_compression_ratio=None,
                on_violation=ziplet.ViolationAction.SKIP,
            ),
        )

    assert isinstance(result, ziplet.ExtractResult)
    assert result.extracted_count == 1
    assert result.skipped_count == 1
    assert result.members[0].status == ziplet.MemberStatus.EXTRACTED
    assert result.members[1].status == ziplet.MemberStatus.SKIPPED
    assert any(v.code == "parent_traversal" for v in result.violations)
    assert (output / "policy" / "safe.txt").read_bytes() == b"safe"
    assert not (tmp_path / "escape.txt").exists()


def test_policy_preview_does_not_write(tmp_path: Path) -> None:
    archive = tmp_path / "preview.zip"
    output = tmp_path / "preview-out"
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("file.txt", b"payload")

    with ziplet.ZipFile(archive) as zf:
        result = zf.extractall(
            output,
            policy=ziplet.ExtractPolicy(
                max_compression_ratio=None,
                preview_only=True,
            ),
        )

    assert isinstance(result, ziplet.ExtractResult)
    assert result.preview_only is True
    assert result.members[0].status == ziplet.MemberStatus.PREVIEWED
    assert not output.exists()


def test_policy_error_exposes_partial_result(tmp_path: Path) -> None:
    archive = tmp_path / "error.zip"
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.txt", b"blocked")

    with ziplet.ZipFile(archive) as zf:
        with pytest.raises(ExtractionError) as raised:
            zf.extractall(
                tmp_path / "out",
                policy=ziplet.ExtractPolicy(max_compression_ratio=None),
            )

    assert raised.value.result.failed_count == 1
    assert raised.value.result.members[0].status == ziplet.MemberStatus.FAILED


def test_policy_rename_does_not_overwrite_existing_target(tmp_path: Path) -> None:
    archive = tmp_path / "rename.zip"
    output = tmp_path / "out"
    output.mkdir()
    (output / "file.txt").write_bytes(b"original")
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("file.txt", b"new")

    with ziplet.ZipFile(archive) as zf:
        result = zf.extractall(
            output,
            policy=ziplet.ExtractPolicy(
                max_compression_ratio=None,
                overwrite_policy=ziplet.OverwritePolicy.RENAME,
            ),
        )

    assert result.members[0].target == output / "file.txt.1"
    assert (output / "file.txt").read_bytes() == b"original"
    assert (output / "file.txt.1").read_bytes() == b"new"


def test_policy_enforces_member_quota_before_writing(tmp_path: Path) -> None:
    archive = tmp_path / "member-limit.zip"
    output = tmp_path / "out"
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("large.bin", b"x" * 32)

    with ziplet.ZipFile(archive) as zf:
        result = zf.extractall(
            output,
            policy=ziplet.ExtractPolicy(
                max_member_size=16,
                max_compression_ratio=None,
                on_violation=ziplet.ViolationAction.SKIP,
            ),
        )

    assert result.members[0].status == ziplet.MemberStatus.SKIPPED
    assert result.members[0].bytes_written == 0
    assert not (output / "large.bin").exists()


def test_policy_enforces_total_quota_across_members(tmp_path: Path) -> None:
    archive = tmp_path / "total-limit.zip"
    output = tmp_path / "out"
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("one.bin", b"1" * 8)
        zf.writestr("two.bin", b"2" * 8)

    with ziplet.ZipFile(archive) as zf:
        result = zf.extractall(
            output,
            policy=ziplet.ExtractPolicy(
                max_member_size=None,
                max_total_uncompressed_size=12,
                max_compression_ratio=None,
                on_violation=ziplet.ViolationAction.SKIP,
            ),
        )

    assert [member.status for member in result.members] == [
        ziplet.MemberStatus.EXTRACTED,
        ziplet.MemberStatus.SKIPPED,
    ]
    assert result.bytes_written == 8
    assert not (output / "two.bin").exists()


def test_policy_aborts_and_removes_partial_output_on_runtime_quota(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "runtime-limit.zip"
    output = tmp_path / "out"
    with ziplet.ZipFile(archive, "w") as writer:
        writer.writestr("payload.bin", b"declared")

    with ziplet.ZipFile(archive) as zf:
        monkeypatch.setattr(
            zf,
            "open",
            lambda *args, **kwargs: io.BytesIO(b"x" * 32),
        )
        with pytest.raises(ExtractionError) as raised:
            zf.extractall(
                output,
                policy=ziplet.ExtractPolicy(
                    max_member_size=16,
                    max_compression_ratio=None,
                ),
            )

    result = raised.value.result
    assert result.members[0].status == ziplet.MemberStatus.FAILED
    assert any(v.code == "actual_member_size" for v in result.violations)
    assert not (output / "payload.bin").exists()
