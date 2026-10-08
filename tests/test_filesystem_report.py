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


def test_report_store_allows_symlink_target_inside_report_root(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    root.mkdir(parents=True)
    target = root / "stored.pdf"
    target.write_bytes(b"private report")
    (root / "job-a.pdf").symlink_to(target)
    store = FileSystemReportArtifactStore(root)

    assert store.get("job-a").content == b"private report"


def test_report_store_escape_does_not_expose_external_bytes(tmp_path, monkeypatch) -> None:
    root = tmp_path / "private" / "reports"
    root.mkdir(parents=True)
    secret = tmp_path / "secret.pdf"
    secret.write_bytes(b"do not expose")
    link = root / "job-a.pdf"
    link.symlink_to(secret)
    store = FileSystemReportArtifactStore(root)
    reads = []
    original = type(secret).read_bytes

    def tracked_read(path):
        reads.append(path)
        return original(path)

    monkeypatch.setattr(type(secret), "read_bytes", tracked_read)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.get("job-a")
    assert reads == []


def test_report_store_missing_artifact_still_raises_file_not_found(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    root.mkdir(parents=True)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(FileNotFoundError):
        store.get("job-missing")


def test_report_store_rejects_root_symlink_retarget_after_initialization(tmp_path) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (external / "job-a.pdf").write_bytes(b"external report")
    root = tmp_path / "reports"
    root.symlink_to(trusted, target_is_directory=True)
    store = FileSystemReportArtifactStore(root)
    root.unlink()
    root.symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.get("job-a")


def test_report_root_retarget_does_not_expose_external_bytes(tmp_path, monkeypatch) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    secret = external / "job-a.pdf"
    secret.write_bytes(b"do not expose")
    root = tmp_path / "reports"
    root.symlink_to(trusted, target_is_directory=True)
    store = FileSystemReportArtifactStore(root)
    root.unlink()
    root.symlink_to(external, target_is_directory=True)
    reads = []
    original = type(secret).read_bytes

    def tracked_read(path):
        reads.append(path)
        return original(path)

    monkeypatch.setattr(type(secret), "read_bytes", tracked_read)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.get("job-a")
    assert reads == []


def test_report_store_accepts_unchanged_symlink_root_target(tmp_path) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    (trusted / "job-a.pdf").write_bytes(b"private report")
    root = tmp_path / "reports"
    root.symlink_to(trusted, target_is_directory=True)
    store = FileSystemReportArtifactStore(root)

    assert store.get("job-a").content == b"private report"


def test_report_store_retarget_is_rejected_even_when_external_artifact_is_missing(tmp_path) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    root = tmp_path / "reports"
    root.symlink_to(trusted, target_is_directory=True)
    store = FileSystemReportArtifactStore(root)
    root.unlink()
    root.symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.get("job-missing")


def test_report_path_rejects_file_symlink_escape(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    root.mkdir(parents=True)
    external = tmp_path / "external.pdf"
    external.write_bytes(b"outside")
    (root / "job-a.pdf").symlink_to(external)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.path_for("job-a")


def test_report_path_symlink_escape_preserves_external_bytes(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    root.mkdir(parents=True)
    external = tmp_path / "external.pdf"
    external.write_bytes(b"keep-me")
    (root / "job-a.pdf").symlink_to(external)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.path_for("job-a").write_bytes(b"overwrite")

    assert external.read_bytes() == b"keep-me"


def test_report_path_rejects_root_retarget_before_write(tmp_path) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    root = tmp_path / "reports"
    root.symlink_to(trusted, target_is_directory=True)
    store = FileSystemReportArtifactStore(root)
    root.unlink()
    root.symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.path_for("job-a")

    assert not (external / "job-a.pdf").exists()


def test_report_path_allows_internal_symlink_write_target(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    root.mkdir(parents=True)
    target = root / "stored.pdf"
    target.write_bytes(b"old")
    (root / "job-a.pdf").symlink_to(target)
    store = FileSystemReportArtifactStore(root)

    store.path_for("job-a").write_bytes(b"new")

    assert target.read_bytes() == b"new"


def test_report_publish_rejects_destination_symlink_escape(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    root.mkdir(parents=True)
    external = tmp_path / "external.pdf"
    external.write_bytes(b"keep-me")
    (root / "job-a.pdf").symlink_to(external)
    temporary = root / ".job-a.tmp"
    temporary.write_bytes(b"new report")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.publish("job-a", temporary)

    assert external.read_bytes() == b"keep-me"
    assert temporary.read_bytes() == b"new report"


def test_report_publish_rejects_root_retarget(tmp_path) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    root = tmp_path / "reports"
    root.symlink_to(trusted, target_is_directory=True)
    store = FileSystemReportArtifactStore(root)
    temporary = trusted / ".job-a.tmp"
    temporary.write_bytes(b"new report")
    root.unlink()
    root.symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.publish("job-a", temporary)

    assert not (external / "job-a.pdf").exists()
    assert temporary.read_bytes() == b"new report"


def test_report_temporary_creation_rejects_root_retarget_after_mkdir(tmp_path, monkeypatch) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    root = tmp_path / "reports"
    root.symlink_to(trusted, target_is_directory=True)
    store = FileSystemReportArtifactStore(root)
    original_mkdir = type(root).mkdir

    def retarget_after_mkdir(path, *args, **kwargs):
        result = original_mkdir(path, *args, **kwargs)
        if path == root and path.is_symlink():
            path.unlink()
            path.symlink_to(external, target_is_directory=True)
        return result

    monkeypatch.setattr(type(root), "mkdir", retarget_after_mkdir)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.create_temporary("job-a")

    assert list(external.iterdir()) == []


def test_report_temporary_creation_stays_inside_private_root(tmp_path) -> None:
    root = tmp_path / "private" / "reports"
    store = FileSystemReportArtifactStore(root)

    temporary = store.create_temporary("job-a")

    assert temporary.parent.resolve() == root.resolve()
    assert temporary.is_file()
    assert temporary.name.startswith(".job-a-")
    assert temporary.suffix == ".pdf"


def test_report_publish_rejects_external_source(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    external = tmp_path / "external.tmp"
    external.write_bytes(b"untrusted")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.publish("job-a", external)

    assert external.read_bytes() == b"untrusted"
    assert not (root / "job-a.pdf").exists()


def test_report_publish_rejects_source_symlink_escape(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    external = tmp_path / "external.tmp"
    external.write_bytes(b"untrusted")
    source = root / ".job-a.tmp"
    source.symlink_to(external)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.publish("job-a", source)

    assert source.is_symlink()
    assert external.read_bytes() == b"untrusted"
    assert not (root / "job-a.pdf").exists()


def test_report_publish_accepts_private_temporary_source(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a.tmp"
    source.write_bytes(b"complete report")
    store = FileSystemReportArtifactStore(root)

    destination = store.publish("job-a", source)

    assert destination == root / "job-a.pdf"
    assert destination.read_bytes() == b"complete report"
    assert not source.exists()


def test_report_publish_rejects_retargeted_source_root(tmp_path) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    root = tmp_path / "reports"
    root.symlink_to(trusted, target_is_directory=True)
    store = FileSystemReportArtifactStore(root)
    source = external / ".job-a.tmp"
    source.write_bytes(b"outside")

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.publish("job-a", source)

    assert source.read_bytes() == b"outside"
    assert not (trusted / "job-a.pdf").exists()
