"""Translate optional Paramiko SFTP opening errors without exposing raw messages."""
from __future__ import annotations

from mcm_solarcheck.infrastructure.ssh_exception_translation import translate_ssh_exception


def open_strict_sftp_session(transport, *, sftp_client_factory):
    if not transport.is_authenticated():
        raise PermissionError("SSH authentication required")
    try:
        client = sftp_client_factory(transport)
    except Exception as exc:
        translated = translate_ssh_exception(exc)
        if translated is not exc:
            raise translated from exc
        raise
    if client is None:
        raise RuntimeError("SFTP client unavailable")
    from mcm_solarcheck.infrastructure.strict_sftp_directory_inspection import StrictReadOnlySFTPSession
    return StrictReadOnlySFTPSession(client)
