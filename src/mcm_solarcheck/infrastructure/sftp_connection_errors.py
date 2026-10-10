"""Stable error categories for optional SSH/SFTP preflight diagnostics."""
from __future__ import annotations


class SFTPPreflightError(RuntimeError):
    category = "unknown"


class SFTPNetworkError(SFTPPreflightError):
    category = "network"


class SFTPAuthenticationError(SFTPPreflightError):
    category = "authentication"


class SFTPPermissionError(SFTPPreflightError):
    category = "permission"


class SFTPHostKeyError(SFTPPreflightError):
    category = "host_key"


class SFTPTimeoutError(SFTPNetworkError):
    category = "timeout"
