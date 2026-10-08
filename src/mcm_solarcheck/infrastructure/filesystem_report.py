"""Filesystem-backed report artifacts for private SFTP-managed storage."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from mcm_solarcheck.services.report_delivery import ReportArtifact


_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odt": "application/vnd.oasis.opendocument.text",
}


class FileSystemReportArtifactStore:
    """Read report artifacts only from a configured private reports directory."""

    def __init__(self, root: str | Path, *, suffix: str = ".pdf") -> None:
        self.root = Path(root)
        self._resolved_root = self.root.expanduser().resolve()
        normalized = suffix.lower()
        if normalized not in _MEDIA_TYPES:
            raise ValueError("unsupported report artifact suffix")
        self.suffix = normalized

    @staticmethod
    def _safe_job_id(job_id: str) -> str:
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError("job_id must be non-empty")
        value = job_id.strip()
        if value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("job_id contains unsafe path characters")
        return value

    def path_for(self, job_id: str) -> Path:
        safe = self._safe_job_id(job_id)
        path = self.root / f"{safe}{self.suffix}"
        try:
            path.resolve().relative_to(self._resolved_root)
        except ValueError as exc:
            raise ValueError(
                "report artifact resolves outside configured report directory"
            ) from exc
        return path

    def create_temporary(self, job_id: str) -> Path:
        destination = self.path_for(job_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            destination.parent.resolve().relative_to(self._resolved_root)
        except ValueError as exc:
            raise ValueError(
                "report artifact resolves outside configured report directory"
            ) from exc
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.stem}-",
            suffix=self.suffix,
            dir=destination.parent,
        )
        os.close(descriptor)
        return Path(temporary_name)

    def publish(self, job_id: str, temporary: str | Path) -> Path:
        destination = self.path_for(job_id)
        source = Path(temporary)
        try:
            source.resolve().relative_to(self._resolved_root)
            destination.parent.resolve().relative_to(self._resolved_root)
            destination.resolve().relative_to(self._resolved_root)
        except ValueError as exc:
            raise ValueError(
                "report artifact resolves outside configured report directory"
            ) from exc
        if source.is_symlink():
            raise ValueError("report temporary source must not be a symlink")
        if not source.is_file():
            raise ValueError("report temporary source must be a regular file")
        if source.resolve() == destination.resolve():
            raise ValueError("report temporary source must differ from destination")
        if source.stat().st_size == 0:
            raise ValueError("report temporary source must not be empty")
        if source.suffix.lower() in _MEDIA_TYPES and source.suffix.lower() != self.suffix:
            raise ValueError("report temporary source suffix does not match report format")
        if not source.name.startswith((f".{destination.stem}-", f".{destination.stem}.")):
            raise ValueError("report temporary source does not match destination job")
        source.replace(destination)
        return destination

    def get(self, job_id: str) -> ReportArtifact:
        path = self.path_for(job_id)
        resolved_path = path.resolve()
        try:
            resolved_path.relative_to(self._resolved_root)
        except ValueError as exc:
            raise ValueError("report artifact resolves outside configured report directory") from exc
        content = resolved_path.read_bytes()
        return ReportArtifact(
            self._safe_job_id(job_id),
            content,
            _MEDIA_TYPES[self.suffix],
            path.name,
        )
