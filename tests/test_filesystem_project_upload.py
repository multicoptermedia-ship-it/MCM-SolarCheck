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
