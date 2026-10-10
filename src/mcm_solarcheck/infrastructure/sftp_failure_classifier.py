"""Classify known Paramiko/SFTP failures without leaking credentials."""
from __future__ import annotations

import socket

from mcm_solarcheck.infrastructure.sftp_connection_errors import (
    SFTPAuthenticationError, SFTPHostKeyError, SFTPNetworkError,
    SFTPPermissionError, SFTPTimeoutError,
)


def classify_sftp_failure(exc: BaseException) -> str:
    if isinstance(exc, SFTPHostKeyError):
        return "host_key"
    if isinstance(exc, SFTPAuthenticationError):
        return "authentication"
    if isinstance(exc, SFTPPermissionError):
        return "permission"
    if isinstance(exc, SFTPTimeoutError) or isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, SFTPNetworkError) or isinstance(exc, (ConnectionError, socket.gaierror)):
        return "network"
    if isinstance(exc, PermissionError):
        return "permission"
    return "unknown"
