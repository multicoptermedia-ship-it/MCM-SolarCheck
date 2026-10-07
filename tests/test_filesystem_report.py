from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.filesystem_report import (
    FileSystemReportArtifactStore,
)


def test_report_store_reads_only_configured_report_directory(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    root.mkdir(parents=True)
    (root / "job-a.pdf").write_bytes(b"private report")
    store = FileSystemReportArtifactStore(root)

    artifact = store.get("job-a")

    assert artifact.job_id == "job-a"
    assert artifact.content == b"private report"
    assert artifact.filename == "job-a.pdf"
    assert artifact.media_type == "application/pdf"


@pytest.mark.parametrize(
    "job_id",
    ["../secret", "../../etc/passwd", "nested/job", r"nested\\job", ".", ".."],
)
def test_report_store_rejects_path_traversal(job_id, tmp_path) -> None:
    store = FileSystemReportArtifactStore(tmp_path / "reports")

    with pytest.raises(ValueError, match="unsafe path"):
        store.path_for(job_id)


def test_report_store_does_not_create_public_or_missing_files(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(FileNotFoundError):
        store.get("job-a")

    assert root.exists() is False


def test_report_file_can_be_manually_deleted_without_state_side_effects(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    root.mkdir(parents=True)
    path = root / "job-a.pdf"
    path.write_bytes(b"private report")
    store = FileSystemReportArtifactStore(root)

    assert store.get("job-a").content == b"private report"
    path.unlink()

    with pytest.raises(FileNotFoundError):
        store.get("job-a")


def test_report_store_rejects_symlink_escape(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    root.mkdir(parents=True)
    secret = tmp_path / "secret.pdf"
    secret.write_bytes(b"server secret")
    (root / "job-a.pdf").symlink_to(secret)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.get("job-a")
