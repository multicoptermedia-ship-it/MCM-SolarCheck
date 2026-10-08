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


def test_report_publish_rejects_internal_source_symlink(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    target = root / "other.pdf"
    target.write_bytes(b"other")
    source = root / ".job-a.tmp"
    source.symlink_to(target)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be a symlink"):
        store.publish("job-a", source)

    assert source.is_symlink()
    assert target.read_bytes() == b"other"
    assert not (root / "job-a.pdf").exists()


def test_report_publish_rejects_dangling_source_symlink(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a.tmp"
    source.symlink_to(root / "missing.pdf")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be a symlink"):
        store.publish("job-a", source)

    assert source.is_symlink()
    assert not (root / "job-a.pdf").exists()


def test_report_publish_preserves_existing_artifact_when_source_is_symlink(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing")
    target = root / "other.pdf"
    target.write_bytes(b"other")
    source = root / ".job-a.tmp"
    source.symlink_to(target)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be a symlink"):
        store.publish("job-a", source)

    assert destination.read_bytes() == b"existing"
    assert target.read_bytes() == b"other"


def test_report_publish_regular_source_still_replaces_existing_artifact(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"old")
    source = root / ".job-a.tmp"
    source.write_bytes(b"new")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source) == destination
    assert destination.read_bytes() == b"new"
    assert not source.exists()


def test_report_publish_rejects_directory_source(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a.tmp"
    source.mkdir()
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must be a regular file"):
        store.publish("job-a", source)

    assert source.is_dir()
    assert not (root / "job-a.pdf").exists()


def test_report_publish_rejects_missing_source(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must be a regular file"):
        store.publish("job-a", root / ".missing.tmp")

    assert not (root / "job-a.pdf").exists()


def test_report_publish_directory_source_preserves_existing_artifact(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing")
    source = root / ".job-a.tmp"
    source.mkdir()
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must be a regular file"):
        store.publish("job-a", source)

    assert destination.read_bytes() == b"existing"
    assert source.is_dir()


def test_report_publish_missing_source_preserves_existing_artifact(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must be a regular file"):
        store.publish("job-a", root / ".missing.tmp")

    assert destination.read_bytes() == b"existing"


def test_report_publish_rejects_same_source_and_destination(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must differ from destination"):
        store.publish("job-a", destination)

    assert destination.read_bytes() == b"existing"


def test_report_publish_rejects_same_destination_via_dot_path(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must differ from destination"):
        store.publish("job-a", root / "." / "job-a.pdf")

    assert destination.read_bytes() == b"existing"


def test_report_publish_same_source_rejection_keeps_existing_content(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-b.pdf"
    destination.write_bytes(b"important report")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must differ from destination"):
        store.publish("job-b", destination)

    assert store.get("job-b").content == b"important report"


def test_report_publish_distinct_temporary_still_replaces_destination(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-b.pdf"
    destination.write_bytes(b"old report")
    source = root / ".job-b-temp.pdf"
    source.write_bytes(b"updated report")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-b", source) == destination
    assert store.get("job-b").content == b"updated report"
    assert not source.exists()


def test_report_publish_rejects_empty_temporary(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a.tmp"
    source.touch()
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be empty"):
        store.publish("job-a", source)

    assert source.is_file()
    assert not (root / "job-a.pdf").exists()


def test_empty_report_temporary_preserves_existing_report(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing")
    source = root / ".job-a.tmp"
    source.touch()
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be empty"):
        store.publish("job-a", source)

    assert destination.read_bytes() == b"existing"
    assert source.stat().st_size == 0


def test_nonempty_report_temporary_publishes_successfully(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a.tmp"
    source.write_bytes(b"report")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source).read_bytes() == b"report"
    assert not source.exists()


def test_nonempty_report_temporary_replaces_existing_artifact(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"old")
    source = root / ".job-a.tmp"
    source.write_bytes(b"new")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source) == destination
    assert destination.read_bytes() == b"new"


def test_report_publish_rejects_mismatched_report_format(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a.docx"
    source.write_bytes(b"wrong format")
    store = FileSystemReportArtifactStore(root, suffix=".pdf")

    with pytest.raises(ValueError, match="suffix does not match"):
        store.publish("job-a", source)

    assert source.read_bytes() == b"wrong format"
    assert not (root / "job-a.pdf").exists()


def test_report_publish_accepts_generic_temporary_suffix(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a.tmp"
    source.write_bytes(b"valid report")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source).read_bytes() == b"valid report"


def test_mismatched_report_format_preserves_existing_artifact(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing")
    source = root / ".job-a.odt"
    source.write_bytes(b"other format")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="suffix does not match"):
        store.publish("job-a", source)

    assert destination.read_bytes() == b"existing"
    assert source.read_bytes() == b"other format"


def test_report_publish_rejects_other_job_temporary(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-b-temp.pdf"
    source.write_bytes(b"other job")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="does not match destination job"):
        store.publish("job-a", source)

    assert source.read_bytes() == b"other job"
    assert not (root / "job-a.pdf").exists()


def test_report_publish_other_job_temporary_preserves_existing_report(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing")
    source = root / ".job-b-temp.pdf"
    source.write_bytes(b"other job")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="does not match destination job"):
        store.publish("job-a", source)

    assert destination.read_bytes() == b"existing"


def test_report_publish_accepts_matching_job_temporary(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"matching job")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source).read_bytes() == b"matching job"


def test_report_publish_rejects_unrelated_private_file(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / "unrelated.tmp"
    source.write_bytes(b"unrelated")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="does not match destination job"):
        store.publish("job-a", source)

    assert source.read_bytes() == b"unrelated"


def test_report_publish_rejects_job_identifier_prefix_collision(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-ab-temp.pdf"
    source.write_bytes(b"other job")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="does not match destination job"):
        store.publish("job-a", source)

    assert source.read_bytes() == b"other job"
    assert not (root / "job-a.pdf").exists()


def test_report_publish_rejects_prefix_collision_with_existing_report(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing")
    source = root / ".job-ab-temp.pdf"
    source.write_bytes(b"other job")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="does not match destination job"):
        store.publish("job-a", source)

    assert destination.read_bytes() == b"existing"


def test_report_publish_accepts_job_temporary_with_dot_separator(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a.tmp"
    source.write_bytes(b"report")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source).read_bytes() == b"report"


def test_report_publish_accepts_job_temporary_with_dash_separator(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a-123.pdf"
    source.write_bytes(b"report")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source).read_bytes() == b"report"


def test_report_publish_rejects_nested_private_temporary(tmp_path) -> None:
    root = tmp_path / "private"
    nested = root / "nested"
    nested.mkdir(parents=True)
    source = nested / ".job-a-temp.pdf"
    source.write_bytes(b"nested")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must share destination directory"):
        store.publish("job-a", source)

    assert source.read_bytes() == b"nested"
    assert not (root / "job-a.pdf").exists()


def test_report_publish_nested_temporary_preserves_existing_report(tmp_path) -> None:
    root = tmp_path / "private"
    nested = root / "nested"
    nested.mkdir(parents=True)
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing")
    source = nested / ".job-a-temp.pdf"
    source.write_bytes(b"nested")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must share destination directory"):
        store.publish("job-a", source)

    assert destination.read_bytes() == b"existing"


def test_report_publish_accepts_temporary_from_same_directory(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"report")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source).read_bytes() == b"report"
    assert not source.exists()


def test_report_publish_rejects_sibling_private_directory_temporary(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    source = sibling / ".job-a-temp.pdf"
    source.write_bytes(b"sibling")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="outside configured report directory"):
        store.publish("job-a", source)

    assert source.read_bytes() == b"sibling"
    assert not (root / "job-a.pdf").exists()


def test_report_get_rejects_directory_named_like_report(tmp_path) -> None:
    root = tmp_path / "private"
    (root / "job-a.pdf").mkdir(parents=True)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must be a regular file"):
        store.get("job-a")


def test_report_get_rejects_symlink_to_directory_inside_private_root(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    directory = root / "directory"
    directory.mkdir()
    (root / "job-a.pdf").symlink_to(directory, target_is_directory=True)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must be a regular file"):
        store.get("job-a")


def test_report_get_still_allows_regular_report_artifact(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    (root / "job-a.pdf").write_bytes(b"report bytes")
    store = FileSystemReportArtifactStore(root)

    assert store.get("job-a").content == b"report bytes"


def test_report_get_still_allows_regular_private_symlink_target(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    (root / "stored.pdf").write_bytes(b"stored report")
    (root / "job-a.pdf").symlink_to(root / "stored.pdf")
    store = FileSystemReportArtifactStore(root)

    assert store.get("job-a").content == b"stored report"


def test_report_get_rejects_empty_report_artifact(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    (root / "job-a.pdf").write_bytes(b"")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be empty"):
        store.get("job-a")


def test_report_get_rejects_empty_private_symlink_target(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    (root / "stored.pdf").write_bytes(b"")
    (root / "job-a.pdf").symlink_to(root / "stored.pdf")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be empty"):
        store.get("job-a")


def test_report_get_accepts_single_byte_artifact(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    (root / "job-a.pdf").write_bytes(b"x")
    store = FileSystemReportArtifactStore(root)

    assert store.get("job-a").content == b"x"


def test_report_get_empty_artifact_does_not_modify_file(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    path = root / "job-a.pdf"
    path.write_bytes(b"")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be empty"):
        store.get("job-a")

    assert path.exists()
    assert path.read_bytes() == b""


def test_report_publish_rejects_directory_destination(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    (root / "job-a.pdf").mkdir()
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"report")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="destination must be a regular file"):
        store.publish("job-a", source)

    assert source.read_bytes() == b"report"
    assert (root / "job-a.pdf").is_dir()


def test_report_publish_rejects_symlink_to_directory_destination(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    directory = root / "existing"
    directory.mkdir()
    (root / "job-a.pdf").symlink_to(directory, target_is_directory=True)
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"report")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="destination must not be a symlink"):
        store.publish("job-a", source)

    assert source.read_bytes() == b"report"
    assert (root / "job-a.pdf").is_symlink()


def test_report_publish_can_replace_existing_regular_report(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"old")
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"new")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source) == destination
    assert destination.read_bytes() == b"new"
    assert not source.exists()


def test_report_publish_can_create_report_when_destination_missing(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"new")
    store = FileSystemReportArtifactStore(root)

    destination = store.publish("job-a", source)

    assert destination.read_bytes() == b"new"
    assert not source.exists()


def test_report_publish_rejects_hardlink_to_external_file(tmp_path) -> None:
    import os

    root = tmp_path / "private"
    root.mkdir()
    external = tmp_path / "external.pdf"
    external.write_bytes(b"external data")
    source = root / ".job-a-temp.pdf"
    os.link(external, source)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be hard-linked"):
        store.publish("job-a", source)

    assert external.read_bytes() == b"external data"
    assert not (root / "job-a.pdf").exists()


def test_report_publish_rejects_hardlink_to_private_file(tmp_path) -> None:
    import os

    root = tmp_path / "private"
    root.mkdir()
    original = root / "other.pdf"
    original.write_bytes(b"other report")
    source = root / ".job-a-temp.pdf"
    os.link(original, source)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be hard-linked"):
        store.publish("job-a", source)

    assert original.read_bytes() == b"other report"
    assert source.exists()


def test_report_publish_hardlink_rejection_preserves_existing_report(tmp_path) -> None:
    import os

    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"existing report")
    original = root / "other.pdf"
    original.write_bytes(b"other report")
    source = root / ".job-a-temp.pdf"
    os.link(original, source)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="must not be hard-linked"):
        store.publish("job-a", source)

    assert destination.read_bytes() == b"existing report"


def test_report_publish_accepts_single_link_temporary(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"report")
    assert source.stat().st_nlink == 1
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source).read_bytes() == b"report"


def test_report_publish_rejects_private_file_symlink_destination(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    target = root / "stored.pdf"
    target.write_bytes(b"stored")
    destination = root / "job-a.pdf"
    destination.symlink_to(target)
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"new")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="destination must not be a symlink"):
        store.publish("job-a", source)

    assert destination.is_symlink()
    assert target.read_bytes() == b"stored"
    assert source.read_bytes() == b"new"


def test_report_publish_rejects_dangling_destination_symlink(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.symlink_to(root / "missing.pdf")
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"new")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="destination must not be a symlink"):
        store.publish("job-a", source)

    assert destination.is_symlink()
    assert source.read_bytes() == b"new"


def test_report_publish_symlink_rejection_preserves_existing_private_target(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    target = root / "other.pdf"
    target.write_bytes(b"other report")
    (root / "job-a.pdf").symlink_to(target)
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"replacement")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="destination must not be a symlink"):
        store.publish("job-a", source)

    assert target.read_bytes() == b"other report"
    assert source.exists()


def test_report_publish_regular_destination_remains_replaceable_after_symlink_guard(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "job-a.pdf"
    destination.write_bytes(b"old")
    source = root / ".job-a-temp.pdf"
    source.write_bytes(b"new")
    store = FileSystemReportArtifactStore(root)

    assert store.publish("job-a", source) == destination
    assert destination.read_bytes() == b"new"


def test_report_get_rejects_external_hardlinked_artifact(tmp_path) -> None:
    import os

    root = tmp_path / "private"
    root.mkdir()
    external = tmp_path / "external.pdf"
    external.write_bytes(b"external data")
    os.link(external, root / "job-a.pdf")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="artifact must not be hard-linked"):
        store.get("job-a")

    assert external.read_bytes() == b"external data"


def test_report_get_rejects_private_hardlinked_artifact(tmp_path) -> None:
    import os

    root = tmp_path / "private"
    root.mkdir()
    other = root / "other.pdf"
    other.write_bytes(b"private report")
    os.link(other, root / "job-a.pdf")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="artifact must not be hard-linked"):
        store.get("job-a")

    assert other.read_bytes() == b"private report"


def test_report_get_accepts_regular_single_link_artifact(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    path = root / "job-a.pdf"
    path.write_bytes(b"report bytes")
    assert path.stat().st_nlink == 1
    store = FileSystemReportArtifactStore(root)

    assert store.get("job-a").content == b"report bytes"


def test_report_get_rejects_hardlink_even_when_target_is_nonempty(tmp_path) -> None:
    import os

    root = tmp_path / "private"
    root.mkdir()
    original = root / "original.pdf"
    original.write_bytes(b"valid nonempty report")
    linked = root / "job-a.pdf"
    os.link(original, linked)
    assert linked.stat().st_size > 0
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="artifact must not be hard-linked"):
        store.get("job-a")


def test_report_get_reads_opened_descriptor_after_path_replacement(tmp_path, monkeypatch) -> None:
    import os
    from mcm_solarcheck.infrastructure import filesystem_report

    root = tmp_path / "private"
    root.mkdir()
    artifact = root / "job-a.pdf"
    artifact.write_bytes(b"original")
    replacement = root / "replacement.pdf"
    replacement.write_bytes(b"replacement")
    real_open = os.open

    def swap_after_open(path, flags, *args, **kwargs):
        descriptor = real_open(path, flags, *args, **kwargs)
        replacement.replace(artifact)
        return descriptor

    monkeypatch.setattr(filesystem_report.os, "open", swap_after_open)
    store = FileSystemReportArtifactStore(root)
    assert store.get("job-a").content == b"original"


def test_report_get_rechecks_opened_descriptor_hardlink_count(tmp_path, monkeypatch) -> None:
    import os
    from mcm_solarcheck.infrastructure import filesystem_report

    root = tmp_path / "private"
    root.mkdir()
    artifact = root / "job-a.pdf"
    artifact.write_bytes(b"original")
    alias = root / "alias.pdf"
    real_open = os.open

    def link_after_open(path, flags, *args, **kwargs):
        descriptor = real_open(path, flags, *args, **kwargs)
        os.link(artifact, alias)
        return descriptor

    monkeypatch.setattr(filesystem_report.os, "open", link_after_open)
    with pytest.raises(ValueError, match="artifact must not be hard-linked"):
        FileSystemReportArtifactStore(root).get("job-a")


def test_report_get_rejects_directory_at_descriptor_boundary(tmp_path, monkeypatch) -> None:
    import os
    from mcm_solarcheck.infrastructure import filesystem_report

    root = tmp_path / "private"
    root.mkdir()
    (root / "job-a.pdf").write_bytes(b"original")
    directory = root / "directory"
    directory.mkdir()
    real_open = os.open

    def open_directory_instead(path, flags, *args, **kwargs):
        return real_open(directory, flags, *args, **kwargs)

    monkeypatch.setattr(filesystem_report.os, "open", open_directory_instead)
    with pytest.raises(ValueError, match="artifact must be a regular file"):
        FileSystemReportArtifactStore(root).get("job-a")


def test_report_get_uses_original_descriptor_when_path_becomes_symlink(tmp_path, monkeypatch) -> None:
    import os
    from mcm_solarcheck.infrastructure import filesystem_report

    root = tmp_path / "private"
    root.mkdir()
    artifact = root / "job-a.pdf"
    artifact.write_bytes(b"original report")
    alternate = root / "alternate.pdf"
    alternate.write_bytes(b"other report")
    real_open = os.open

    def retarget_after_open(path, flags, *args, **kwargs):
        descriptor = real_open(path, flags, *args, **kwargs)
        artifact.unlink()
        artifact.symlink_to(alternate)
        return descriptor

    monkeypatch.setattr(filesystem_report.os, "open", retarget_after_open)
    assert FileSystemReportArtifactStore(root).get("job-a").content == b"original report"


def test_report_get_rejects_fifo_without_waiting_for_writer(tmp_path) -> None:
    import os

    root = tmp_path / "private"
    root.mkdir()
    os.mkfifo(root / "job-a.pdf")
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="artifact must be a regular file"):
        store.get("job-a")


def test_report_get_rejects_private_fifo_symlink_without_waiting(tmp_path) -> None:
    import os

    root = tmp_path / "private"
    root.mkdir()
    fifo = root / "pipe"
    os.mkfifo(fifo)
    (root / "job-a.pdf").symlink_to(fifo)
    store = FileSystemReportArtifactStore(root)

    with pytest.raises(ValueError, match="artifact must be a regular file"):
        store.get("job-a")


def test_report_get_opens_file_with_nonblocking_flag(tmp_path, monkeypatch) -> None:
    import os
    from mcm_solarcheck.infrastructure import filesystem_report

    root = tmp_path / "private"
    root.mkdir()
    (root / "job-a.pdf").write_bytes(b"report")
    real_open = os.open
    observed = []

    def inspect_flags(path, flags, *args, **kwargs):
        observed.append(flags)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(filesystem_report.os, "open", inspect_flags)
    assert FileSystemReportArtifactStore(root).get("job-a").content == b"report"
    assert observed and observed[0] & os.O_NONBLOCK


def test_report_get_rejects_unix_socket_artifact(tmp_path) -> None:
    import socket

    root = tmp_path / "private"
    root.mkdir()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(str(root / "job-a.pdf"))
        with pytest.raises((ValueError, OSError)):
            FileSystemReportArtifactStore(root).get("job-a")
    finally:
        sock.close()


def test_report_publish_syncs_temporary_file_before_replacement(tmp_path, monkeypatch) -> None:
    import os
    from mcm_solarcheck.infrastructure import filesystem_report

    root = tmp_path / "reports"
    store = FileSystemReportArtifactStore(root)
    source = store.create_temporary("job-a")
    source.write_bytes(b"report")
    real_fsync = os.fsync
    synced = []

    def record_sync(descriptor):
        synced.append(os.fstat(descriptor).st_size)
        return real_fsync(descriptor)

    monkeypatch.setattr(filesystem_report.os, "fsync", record_sync)
    store.publish("job-a", source)
    assert synced == [len(b"report")]


def test_report_publish_sync_failure_preserves_existing_report(tmp_path, monkeypatch) -> None:
    from mcm_solarcheck.infrastructure import filesystem_report

    root = tmp_path / "reports"
    store = FileSystemReportArtifactStore(root)
    existing = root / "job-a.pdf"
    source = store.create_temporary("job-a")
    existing.write_bytes(b"previous")
    source.write_bytes(b"replacement")

    def fail_sync(descriptor):
        raise OSError("sync failed")

    monkeypatch.setattr(filesystem_report.os, "fsync", fail_sync)
    with pytest.raises(OSError, match="sync failed"):
        store.publish("job-a", source)
    assert existing.read_bytes() == b"previous"
    assert source.read_bytes() == b"replacement"


def test_report_publish_rechecks_source_descriptor_after_hardlink_race(tmp_path, monkeypatch) -> None:
    import os
    from mcm_solarcheck.infrastructure import filesystem_report

    root = tmp_path / "reports"
    store = FileSystemReportArtifactStore(root)
    source = store.create_temporary("job-a")
    source.write_bytes(b"report")
    real_open = os.open
    alias = root / "alias.pdf"

    def link_after_open(path, flags, *args, **kwargs):
        descriptor = real_open(path, flags, *args, **kwargs)
        os.link(source, alias)
        return descriptor

    monkeypatch.setattr(filesystem_report.os, "open", link_after_open)
    with pytest.raises(ValueError, match="temporary source must not be hard-linked"):
        store.publish("job-a", source)
    assert not (root / "job-a.pdf").exists()


def test_report_publish_rechecks_source_descriptor_after_truncation(tmp_path, monkeypatch) -> None:
    import os
    from mcm_solarcheck.infrastructure import filesystem_report

    root = tmp_path / "reports"
    store = FileSystemReportArtifactStore(root)
    source = store.create_temporary("job-a")
    source.write_bytes(b"report")
    real_open = os.open

    def truncate_after_open(path, flags, *args, **kwargs):
        descriptor = real_open(path, flags, *args, **kwargs)
        source.write_bytes(b"")
        return descriptor

    monkeypatch.setattr(filesystem_report.os, "open", truncate_after_open)
    with pytest.raises(ValueError, match="temporary source must not be empty"):
        store.publish("job-a", source)
    assert not (root / "job-a.pdf").exists()


def test_report_publish_syncs_directory_after_source_file(tmp_path, monkeypatch) -> None:
    import os
    import stat
    from mcm_solarcheck.infrastructure import filesystem_report

    store = FileSystemReportArtifactStore(tmp_path / "reports")
    source = store.create_temporary("job-a")
    source.write_bytes(b"report")
    observed = []
    real_fsync = os.fsync

    def record_sync(descriptor):
        mode = os.fstat(descriptor).st_mode
        observed.append("directory" if stat.S_ISDIR(mode) else "file")
        return real_fsync(descriptor)

    monkeypatch.setattr(filesystem_report.os, "fsync", record_sync)
    store.publish("job-a", source)
    assert observed == ["file", "directory"]


def test_report_publish_directory_sync_failure_reports_error(tmp_path, monkeypatch) -> None:
    import os
    import stat
    from mcm_solarcheck.infrastructure import filesystem_report

    store = FileSystemReportArtifactStore(tmp_path / "reports")
    source = store.create_temporary("job-a")
    source.write_bytes(b"report")
    real_fsync = os.fsync

    def fail_directory_sync(descriptor):
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise OSError("directory sync failed")
        return real_fsync(descriptor)

    monkeypatch.setattr(filesystem_report.os, "fsync", fail_directory_sync)
    with pytest.raises(OSError, match="directory sync failed"):
        store.publish("job-a", source)
    assert (store.root / "job-a.pdf").read_bytes() == b"report"


def test_report_publish_directory_sync_uses_destination_parent(tmp_path, monkeypatch) -> None:
    import os
    import stat
    from mcm_solarcheck.infrastructure import filesystem_report

    root = tmp_path / "reports"
    store = FileSystemReportArtifactStore(root)
    source = store.create_temporary("job-a")
    source.write_bytes(b"report")
    real_open = os.open
    opened_directories = []

    def record_open(path, flags, *args, **kwargs):
        descriptor = real_open(path, flags, *args, **kwargs)
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            opened_directories.append(os.fspath(path))
        return descriptor

    monkeypatch.setattr(filesystem_report.os, "open", record_open)
    store.publish("job-a", source)
    assert opened_directories == [os.fspath(root)]
