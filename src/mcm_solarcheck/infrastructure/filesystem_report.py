"""Filesystem-backed report artifacts for private SFTP-managed storage."""

from __future__ import annotations

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
        return self.root / f"{safe}{self.suffix}"

    def get(self, job_id: str) -> ReportArtifact:
        path = self.path_for(job_id)
        content = path.read_bytes()
        return ReportArtifact(
            self._safe_job_id(job_id),
            content,
            _MEDIA_TYPES[self.suffix],
            path.name,
        )
