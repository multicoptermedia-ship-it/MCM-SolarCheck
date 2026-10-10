"""Lexical SFTP path isolation for customer/project-scoped read-only probes.

Server-side symlink behavior is NOT established by lexical checks.
"""
from __future__ import annotations

import posixpath


def project_sftp_directory(root: str, customer_id: str, project_id: str) -> str:
    from mcm_solarcheck.services.sftp_project_session_manager import SFTPProjectContext
    SFTPProjectContext(customer_id, project_id)
    if not isinstance(root, str) or not root.startswith("/") or "\\x00" in root:
        raise ValueError("absolute SFTP root required")
    parts = root.split("/")
    if any(part in (".", "..") for part in parts):
        raise ValueError("noncanonical SFTP root")
    normalized = posixpath.normpath(root)
    return posixpath.join(normalized, customer_id, project_id)


def require_project_sftp_path(root: str, customer_id: str, project_id: str, path: str) -> str:
    base = project_sftp_directory(root, customer_id, project_id)
    if not isinstance(path, str) or not path.startswith("/") or "\\x00" in path:
        raise ValueError("absolute SFTP path required")
    if any(part in (".", "..") for part in path.split("/")):
        raise PermissionError("noncanonical SFTP path")
    normalized = posixpath.normpath(path)
    if normalized != base and not normalized.startswith(base + "/"):
        raise PermissionError("SFTP path outside project")
    return normalized
