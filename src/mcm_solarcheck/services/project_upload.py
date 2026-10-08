"""Validated application boundary for customer project uploads."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePath
from pathlib import Path
from typing import Callable, Protocol


DEFAULT_MAX_UPLOAD_BYTES = 250 * 1024 * 1024
ALLOWED_UPLOAD_TYPES = frozenset(
    {
        "image/jpeg",
        "image/tiff",
        "application/octet-stream",
    }
)


@dataclass(frozen=True)
class ProjectUploadRequest:
    customer_id: str
    project_id: str
    filename: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class StoredProjectUpload:
    customer_id: str
    project_id: str
    filename: str
    content_type: str
    size_bytes: int
    sha256_hex: str


@dataclass(frozen=True)
class ValidatedProjectUpload:
    request: ProjectUploadRequest
    size_bytes: int
    sha256_hex: str


class ProjectUploadStore(Protocol):
    def store(self, upload: ValidatedProjectUpload) -> None: ...

    def project_directory(self, customer_id: str, project_id: str) -> Path: ...


class ProjectUploadService:
    def __init__(
        self,
        store_upload: Callable[[ValidatedProjectUpload], None],
        project_belongs_to_customer: Callable[[str, str], bool],
        *,
        max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    ) -> None:
        if max_upload_bytes <= 0:
            raise ValueError("max_upload_bytes must be positive")
        self._store_upload = store_upload
        self._project_belongs_to_customer = project_belongs_to_customer
        self._max_upload_bytes = max_upload_bytes

    def upload(self, request: ProjectUploadRequest) -> StoredProjectUpload:
        customer_id = request.customer_id.strip()
        project_id = request.project_id.strip()
        filename = request.filename.strip()
        content_type = request.content_type.split(";", 1)[0].strip().lower()

        if not customer_id or not project_id:
            raise ValueError("customer and project are required")
        if (
            not filename
            or PurePath(filename).name != filename
            or "\\" in filename
            or "\x00" in filename
            or filename in {".", ".."}
        ):
            raise ValueError("upload filename is invalid")
        if content_type not in ALLOWED_UPLOAD_TYPES:
            raise ValueError("upload content type is not supported")
        if not request.content:
            raise ValueError("upload must not be empty")
        if content_type == "image/jpeg" and not request.content.startswith(b"\xff\xd8\xff"):
            raise ValueError("JPEG upload signature is invalid")
        if content_type == "image/tiff" and not (
            request.content.startswith(b"II*\x00")
            or request.content.startswith(b"MM\x00*")
        ):
            raise ValueError("TIFF upload signature is invalid")
        if len(request.content) > self._max_upload_bytes:
            raise ValueError("upload is too large")
        if not self._project_belongs_to_customer(customer_id, project_id):
            raise PermissionError("project is not available to customer")

        normalized = ProjectUploadRequest(
            customer_id=customer_id,
            project_id=project_id,
            filename=filename,
            content_type=content_type,
            content=request.content,
        )
        size_bytes = len(normalized.content)
        sha256_hex = sha256(normalized.content).hexdigest()
        self._store_upload(
            ValidatedProjectUpload(
                request=normalized,
                size_bytes=size_bytes,
                sha256_hex=sha256_hex,
            )
        )
        return StoredProjectUpload(
            customer_id=customer_id,
            project_id=project_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256_hex=sha256_hex,
        )
