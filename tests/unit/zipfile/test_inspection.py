from pathlib import Path

import ziplet
from ziplet.zipfile.info import ZipInfo


def test_inspection_reports_metadata_findings_without_extraction(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "inspect.zip"
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr("same.txt", b"one")
        zf.writestr("same.txt", b"two")
        zf.writestr("../same.txt", b"escape")
        zf.writestr("large.bin", b"x" * 8)

    with ziplet.ZipFile(archive) as zf:
        report = zf.inspect(
            tmp_path / "not-created",
            ziplet.ExtractPolicy(
                max_member_size=4,
                max_compression_ratio=None,
                on_violation=ziplet.ViolationAction.SKIP,
            ),
        )

    assert report.total_entries == 4
    assert report.total_compressed_size > 0
    assert report.total_uncompressed_size == 20
    assert report.duplicate_member_names == ("same.txt",)
    assert report.duplicate_targets == (tmp_path / "not-created" / "same.txt",)
    assert report.suspicious_paths == ("../same.txt",)
    assert report.large_members == ("../same.txt", "large.bin")
    assert report.members[2].violations[0].action == ziplet.ViolationAction.SKIP
    assert not (tmp_path / "not-created").exists()


def test_inspection_distinguishes_symlinks_and_special_files(tmp_path: Path) -> None:
    archive = tmp_path / "types.zip"
    link = ZipInfo("link")
    link.external_attr = (0o120777 << 16) | 0xA000
    special = ZipInfo("device")
    special.external_attr = 0o010000 << 16
    with ziplet.ZipFile(archive, "w") as zf:
        zf.writestr(link, "target")
        zf.writestr(special, b"data")

    with ziplet.ZipFile(archive) as zf:
        report = zf.inspect()

    assert report.symlinks == ("link",)
    assert report.special_files == ("device",)
    assert any(v.code == "symlink" for v in report.members[0].violations)
