from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.filesystem_project_upload import (
    FileSystemProjectUploadStore,
)
from mcm_solarcheck.services.project_upload import (
    ProjectUploadRequest,
    ValidatedProjectUpload,
)


def upload(*, customer_id="user-1", project_id="P-1", filename="thermal.jpg"):
    request = ProjectUploadRequest(
        customer_id=customer_id,
        project_id=project_id,
        filename=filename,
        content_type="image/jpeg",
        content=b"validated-content",
    )
    return ValidatedProjectUpload(
        request=request,
        size_bytes=len(request.content),
        sha256_hex="metadata-already-validated-by-service",
    )


def test_filesystem_upload_store_isolates_customer_project_directories(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")

    store.store(upload())

    directory = store.project_directory("user-1", "P-1")
    assert directory == (tmp_path / "uploads" / "user-1" / "P-1").resolve()
    assert (directory / "thermal.jpg").read_bytes() == b"validated-content"


@pytest.mark.parametrize(
    ("customer_id", "project_id"),
    [
        ("../user", "P-1"),
        (r"user\\other", "P-1"),
        ("user-1", "../P-1"),
        ("user-1", r"P\\other"),
        ("user\x00", "P-1"),
    ],
)
def test_filesystem_upload_store_rejects_unsafe_identity_segments(
    tmp_path, customer_id, project_id
) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")

    with pytest.raises(ValueError):
        store.store(upload(customer_id=customer_id, project_id=project_id))

    assert list(store.root.iterdir()) == []


def test_project_directory_resolver_does_not_create_directory(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")

    directory = store.project_directory("user-1", "P-1")

    assert directory == store.root / "user-1" / "P-1"
    assert not directory.exists()


def test_upload_store_rejects_customer_directory_symlink_escape(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    external = tmp_path / "external"
    external.mkdir()
    (store.root / "user-1").symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="outside configured root"):
        store.store(upload())

    assert not (external / "P-1" / "thermal.jpg").exists()


def test_upload_store_rejects_project_directory_symlink_escape(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    customer = store.root / "user-1"
    customer.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (customer / "P-1").symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="outside configured root"):
        store.store(upload())

    assert not (external / "thermal.jpg").exists()


def test_upload_store_allows_project_symlink_inside_upload_root(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    customer = store.root / "user-1"
    customer.mkdir()
    target = store.root / "stored-project"
    target.mkdir()
    (customer / "P-1").symlink_to(target, target_is_directory=True)

    store.store(upload())

    assert (target / "thermal.jpg").read_bytes() == b"validated-content"


def test_upload_escape_is_rejected_before_external_project_directory_creation(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    external = tmp_path / "external"
    external.mkdir()
    (store.root / "user-1").symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="outside configured root"):
        store.project_directory("user-1", "P-1")

    assert not (external / "P-1").exists()


def test_upload_store_rejects_file_symlink_escape(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    external = tmp_path / "external.jpg"
    external.write_bytes(b"outside")
    (directory / "thermal.jpg").symlink_to(external)

    with pytest.raises(ValueError, match="outside configured root"):
        store.store(upload())


def test_upload_store_allows_file_symlink_inside_upload_root(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    target = store.root / "shared.jpg"
    target.write_bytes(b"old")
    (directory / "thermal.jpg").symlink_to(target)

    store.store(upload())

    assert target.read_bytes() == b"validated-content"


def test_upload_file_symlink_escape_does_not_modify_external_bytes(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    external = tmp_path / "external.jpg"
    external.write_bytes(b"keep-me")
    (directory / "thermal.jpg").symlink_to(external)

    with pytest.raises(ValueError, match="outside configured root"):
        store.store(upload())

    assert external.read_bytes() == b"keep-me"


def test_upload_store_writes_regular_file_within_private_root(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")

    store.store(upload(filename="regular.jpg"))

    destination = store.root / "user-1" / "P-1" / "regular.jpg"
    assert destination.is_file()
    assert not destination.is_symlink()
    assert destination.read_bytes() == b"validated-content"


def test_upload_store_rechecks_directory_after_creation(tmp_path, monkeypatch) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    external = tmp_path / "external"
    external.mkdir()
    original_mkdir = type(directory).mkdir

    def retarget_after_mkdir(path, *args, **kwargs):
        result = original_mkdir(path, *args, **kwargs)
        if path == directory and path.is_dir() and not path.is_symlink():
            path.rmdir()
            path.symlink_to(external, target_is_directory=True)
        return result

    monkeypatch.setattr(type(directory), "mkdir", retarget_after_mkdir)

    with pytest.raises(ValueError, match="outside configured root"):
        store.store(upload())

    assert not (external / "thermal.jpg").exists()


def test_upload_parent_retarget_before_write_preserves_external_directory(tmp_path, monkeypatch) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    original_resolve = type(directory).resolve
    destination = directory / "thermal.jpg"
    calls = {"destination": 0}

    def retarget_on_destination_resolve(path, *args, **kwargs):
        resolved = original_resolve(path, *args, **kwargs)
        if path == destination:
            calls["destination"] += 1
            if calls["destination"] == 1:
                directory.rmdir()
                directory.symlink_to(external, target_is_directory=True)
        return resolved

    monkeypatch.setattr(type(directory), "resolve", retarget_on_destination_resolve)

    with pytest.raises(ValueError, match="outside configured root"):
        store.store(upload())

    assert not (external / "thermal.jpg").exists()


def test_upload_rechecks_still_allow_regular_private_write(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")

    store.store(upload(filename="race-safe.jpg"))

    destination = store.root / "user-1" / "P-1" / "race-safe.jpg"
    assert destination.read_bytes() == b"validated-content"


def test_upload_rejects_directory_at_destination(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    destination = store.project_directory("user-1", "P-1") / "thermal.jpg"
    destination.mkdir(parents=True)
    with pytest.raises(ValueError, match="must be a regular file"):
        store.store(upload())
    assert destination.is_dir()


def test_upload_rejects_internal_directory_symlink_as_destination(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    target = store.root / "directory-target"
    target.mkdir()
    destination = directory / "thermal.jpg"
    destination.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="must be a regular file"):
        store.store(upload())
    assert destination.is_symlink()
    assert list(target.iterdir()) == []


def test_upload_rejects_fifo_destination_without_blocking(tmp_path) -> None:
    import os
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO files not supported")
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    destination = store.project_directory("user-1", "P-1") / "thermal.jpg"
    destination.parent.mkdir(parents=True)
    os.mkfifo(destination)
    with pytest.raises(ValueError, match="must be a regular file"):
        store.store(upload())
    assert destination.exists()


def test_upload_still_overwrites_existing_regular_file(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    destination = store.project_directory("user-1", "P-1") / "thermal.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"previous")
    store.store(upload())
    assert destination.read_bytes() == b"validated-content"


def test_upload_rejects_dangling_internal_destination_symlink(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    target = store.root / "missing.jpg"
    destination = directory / "thermal.jpg"
    destination.symlink_to(target)
    with pytest.raises(ValueError, match="dangling symlink"):
        store.store(upload())
    assert not target.exists()
    assert destination.is_symlink()


def test_upload_rejects_dangling_relative_destination_symlink(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    destination = directory / "thermal.jpg"
    destination.symlink_to("missing.jpg")
    with pytest.raises(ValueError, match="dangling symlink"):
        store.store(upload())
    assert not (directory / "missing.jpg").exists()


def test_upload_dangling_symlink_rejection_preserves_other_files(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    existing = directory / "existing.jpg"
    existing.write_bytes(b"preserved")
    (directory / "thermal.jpg").symlink_to("missing.jpg")
    with pytest.raises(ValueError, match="dangling symlink"):
        store.store(upload())
    assert existing.read_bytes() == b"preserved"


def test_upload_still_creates_missing_regular_destination(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    destination = store.project_directory("user-1", "P-1") / "thermal.jpg"
    assert not destination.exists()
    store.store(upload())
    assert destination.read_bytes() == b"validated-content"
    assert not destination.is_symlink()


def test_upload_rejects_hardlink_to_external_file(tmp_path) -> None:
    import os
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    external = tmp_path / "external.jpg"
    external.write_bytes(b"preserve")
    os.link(external, directory / "thermal.jpg")
    with pytest.raises(ValueError, match="must not be hard-linked"):
        store.store(upload())
    assert external.read_bytes() == b"preserve"


def test_upload_rejects_hardlink_to_private_sibling_file(tmp_path) -> None:
    import os
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    sibling = directory / "sibling.jpg"
    sibling.write_bytes(b"preserve sibling")
    os.link(sibling, directory / "thermal.jpg")
    with pytest.raises(ValueError, match="must not be hard-linked"):
        store.store(upload())
    assert sibling.read_bytes() == b"preserve sibling"


def test_upload_rejects_multiple_hardlinks_to_same_destination(tmp_path) -> None:
    import os
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    destination = directory / "thermal.jpg"
    destination.write_bytes(b"preserve")
    os.link(destination, directory / "alias-1.jpg")
    os.link(destination, directory / "alias-2.jpg")
    with pytest.raises(ValueError, match="must not be hard-linked"):
        store.store(upload())
    assert (directory / "alias-2.jpg").read_bytes() == b"preserve"


def test_upload_still_overwrites_single_link_file(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    destination = store.project_directory("user-1", "P-1") / "thermal.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"old")
    assert destination.stat().st_nlink == 1
    store.store(upload())
    assert destination.read_bytes() == b"validated-content"


def test_upload_store_rejects_parent_traversal_filename(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    with pytest.raises(ValueError, match="filename is invalid"):
        store.store(upload(filename="../escape.jpg"))
    assert not (store.root / "user-1" / "escape.jpg").exists()


def test_upload_store_rejects_absolute_filename(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    external = tmp_path / "external.jpg"
    with pytest.raises(ValueError, match="filename is invalid"):
        store.store(upload(filename=str(external)))
    assert not external.exists()


@pytest.mark.parametrize("filename", ["nested/file.jpg", r"nested\\file.jpg", "bad\\x00name.jpg", ".", ".."])
def test_upload_store_rejects_unsafe_filename_segments(tmp_path, filename) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    with pytest.raises(ValueError, match="filename is invalid"):
        store.store(upload(filename=filename))


def test_upload_store_accepts_simple_filename_after_boundary_validation(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    store.store(upload(filename="validated-image.jpg"))
    destination = store.project_directory("user-1", "P-1") / "validated-image.jpg"
    assert destination.read_bytes() == b"validated-content"


def test_invalid_filename_does_not_create_customer_directory(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    with pytest.raises(ValueError, match="filename is invalid"):
        store.store(upload(filename="../escape.jpg"))
    assert not (store.root / "user-1").exists()


def test_invalid_filename_does_not_create_project_directory(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    customer = store.root / "user-1"
    customer.mkdir()
    with pytest.raises(ValueError, match="filename is invalid"):
        store.store(upload(filename="/absolute.jpg"))
    assert not (customer / "P-1").exists()


def test_invalid_filename_preserves_existing_project_contents(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    directory = store.project_directory("user-1", "P-1")
    directory.mkdir(parents=True)
    existing = directory / "existing.jpg"
    existing.write_bytes(b"unchanged")
    with pytest.raises(ValueError, match="filename is invalid"):
        store.store(upload(filename="nested/thermal.jpg"))
    assert existing.read_bytes() == b"unchanged"
    assert sorted(p.name for p in directory.iterdir()) == ["existing.jpg"]


def test_valid_filename_still_creates_customer_and_project_directories(tmp_path) -> None:
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    store.store(upload(filename="new-image.jpg"))
    destination = store.root / "user-1" / "P-1" / "new-image.jpg"
    assert destination.read_bytes() == b"validated-content"
    assert destination.parent.is_dir()


def test_upload_atomic_replace_preserves_previous_file_on_replace_failure(tmp_path, monkeypatch) -> None:
    import os
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    destination = store.project_directory("user-1", "P-1") / "thermal.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"previous")

    def fail_replace(source, target):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replacement failure"):
        store.store(upload())
    assert destination.read_bytes() == b"previous"
    assert sorted(p.name for p in destination.parent.iterdir()) == ["thermal.jpg"]


def test_upload_atomic_write_preserves_existing_file_on_fsync_failure(tmp_path, monkeypatch) -> None:
    import os
    store = FileSystemProjectUploadStore(tmp_path / "uploads")
    destination = store.project_directory("user-1", "P-1") / "thermal.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"previous")

    def fail_fsync(fd):
        raise OSError("simulated fsync failure")

    monkeypatch.setattr(os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="simulated fsync failure"):
        store.store(upload())
    assert destination.read_bytes() == b"previous"
    assert sorted(p.name for p in destination.parent.iterdir()) == ["thermal.jpg"]
