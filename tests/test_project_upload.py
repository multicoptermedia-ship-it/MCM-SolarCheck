import hashlib

import pytest

from mcm_solarcheck.services.project_upload import (
    ProjectUploadRequest,
    ProjectUploadService,
)


def request(**changes):
    values = {
        "customer_id": "user-1",
        "project_id": "P-1",
        "filename": "thermal-001.jpg",
        "content_type": "image/jpeg",
        "content": b"\xff\xd8\xffimage-data",
    }
    values.update(changes)
    return ProjectUploadRequest(**values)


def test_upload_is_stored_only_for_customer_project() -> None:
    stored = []
    ownership_checks = []
    service = ProjectUploadService(
        stored.append,
        lambda customer_id, project_id: ownership_checks.append(
            (customer_id, project_id)
        ) or True,
    )

    result = service.upload(request())

    assert ownership_checks == [("user-1", "P-1")]
    assert len(stored) == 1
    assert stored[0].customer_id == "user-1"
    assert stored[0].project_id == "P-1"
    assert result.sha256_hex == hashlib.sha256(stored[0].content).hexdigest()
    assert result.filename == "thermal-001.jpg"
    assert result.size_bytes == len(b"\xff\xd8\xffimage-data")


def test_upload_rejects_project_from_another_customer_before_storage() -> None:
    stored = []
    service = ProjectUploadService(stored.append, lambda customer_id, project_id: False)

    with pytest.raises(PermissionError):
        service.upload(request())

    assert stored == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("customer_id", " "),
        ("project_id", ""),
        ("filename", ""),
        ("filename", "../thermal.jpg"),
        ("filename", "folder/thermal.jpg"),
        ("content_type", "text/plain"),
        ("content", b""),
    ],
)
def test_upload_rejects_invalid_metadata_before_storage(field, value) -> None:
    stored = []
    ownership_called = []
    service = ProjectUploadService(
        stored.append,
        lambda customer_id, project_id: ownership_called.append(True) or True,
    )

    with pytest.raises(ValueError):
        service.upload(request(**{field: value}))

    assert stored == []
    assert ownership_called == []


def test_upload_rejects_file_above_configured_size_limit() -> None:
    stored = []
    service = ProjectUploadService(
        stored.append,
        lambda customer_id, project_id: True,
        max_upload_bytes=4,
    )

    with pytest.raises(ValueError):
        service.upload(request(content=b"12345"))

    assert stored == []


def test_upload_normalizes_content_type_parameters() -> None:
    stored = []
    service = ProjectUploadService(stored.append, lambda customer_id, project_id: True)

    result = service.upload(request(content_type="Image/JPEG; charset=binary"))

    assert result.content_type == "image/jpeg"
    assert stored[0].content_type == "image/jpeg"


@pytest.mark.parametrize(
    ("content_type", "content"),
    [
        ("image/jpeg", b"not-a-jpeg"),
        ("image/tiff", b"not-a-tiff"),
    ],
)
def test_upload_rejects_image_content_with_invalid_signature(content_type, content) -> None:
    stored = []
    ownership_called = []
    service = ProjectUploadService(
        stored.append,
        lambda customer_id, project_id: ownership_called.append(True) or True,
    )

    with pytest.raises(ValueError):
        service.upload(request(content_type=content_type, content=content))

    assert stored == []
    assert ownership_called == []


@pytest.mark.parametrize("content", [b"II*\x00data", b"MM\x00*data"])
def test_upload_accepts_both_tiff_byte_orders(content) -> None:
    stored = []
    service = ProjectUploadService(stored.append, lambda customer_id, project_id: True)

    result = service.upload(
        request(filename="thermal-001.tiff", content_type="image/tiff", content=content)
    )

    assert result.content_type == "image/tiff"
    assert stored[0].content == content
