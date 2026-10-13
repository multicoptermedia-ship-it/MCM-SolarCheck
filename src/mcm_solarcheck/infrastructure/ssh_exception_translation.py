"""Map known SSH-library failures to stable, non-secret diagnostics.

Paramiko exception imports are optional. Unknown errors remain unknown.
"""
from __future__ import annotations

import errno
import socket

from mcm_solarcheck.infrastructure.sftp_connection_errors import (
    SFTPAuthenticationError, SFTPNetworkError, SFTPPermissionError, SFTPTimeoutError,
)


def translate_ssh_exception(exc: Exception) -> Exception:
    if isinstance(exc, (SFTPAuthenticationError, SFTPNetworkError, SFTPPermissionError)):
        return exc
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return SFTPTimeoutError("SSH operation timed out")
    if isinstance(exc, PermissionError):
        return SFTPPermissionError("SFTP access denied")
    if isinstance(exc, OSError):
        if exc.errno in (errno.EACCES, errno.EPERM):
            return SFTPPermissionError("SFTP access denied")
        if exc.errno in (errno.ECONNREFUSED, errno.ECONNRESET, errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EPIPE):
            return SFTPNetworkError("SSH network failure")
    try:
        from paramiko.ssh_exception import AuthenticationException, NoValidConnectionsError
    except ImportError:
        return exc
    if isinstance(exc, AuthenticationException):
        return SFTPAuthenticationError("SSH authentication rejected")
    if isinstance(exc, NoValidConnectionsError):
        return SFTPNetworkError("SSH connection unavailable")
    return exc
