"""Private filesystem storage for validated online project uploads."""

from __future__ import annotations

from pathlib import Path

from mcm_solarcheck.services.project_upload import ValidatedProjectUpload


class FileSystemProjectUploadStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _segment(value: str, field: str) -> str:
        normalized = value.strip()
        if (
            not normalized
            or normalized in {".", ".."}
            or "/" in normalized
            or "\\" in normalized
            or "\x00" in normalized
        ):
            raise ValueError(f"{field} is invalid")
        return normalized

    def project_directory(self, customer_id: str, project_id: str) -> Path:
        customer = self._segment(customer_id, "customer_id")
        project = self._segment(project_id, "project_id")
        directory = self.root / customer / project
        try:
            directory.resolve().relative_to(self.root)
        except ValueError as exc:
            raise ValueError("project upload directory resolves outside configured root") from exc
        return directory

    def store(self, upload: ValidatedProjectUpload) -> None:
        request = upload.request
        directory = self.project_directory(request.customer_id, request.project_id)
        directory.mkdir(parents=True, exist_ok=True)
        try:
            directory.resolve().relative_to(self.root)
        except ValueError as exc:
            raise ValueError("project upload directory resolves outside configured root") from exc
        destination = directory / request.filename
        try:
            destination.resolve().relative_to(self.root)
        except ValueError as exc:
            raise ValueError("project upload file resolves outside configured root") from exc
        destination.write_bytes(request.content)
