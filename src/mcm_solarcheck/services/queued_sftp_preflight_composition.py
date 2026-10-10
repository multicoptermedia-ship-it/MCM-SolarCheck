"""Explicit queue/SFTP preflight composition; never starts background work."""
from __future__ import annotations

from mcm_solarcheck.services.queued_sftp_preflight import QueuedSFTPPreflight
from mcm_solarcheck.services.queued_sftp_preflight_batch import QueuedSFTPPreflightBatch
from mcm_solarcheck.services.sftp_project_session_manager import SFTPProjectSessionManager


def build_queued_sftp_preflight(store, connector, config, *, batch_size=100, max_sessions=2):
    sessions = SFTPProjectSessionManager(connector, config, max_sessions=max_sessions)
    return QueuedSFTPPreflightBatch(
        store, QueuedSFTPPreflight(sessions), batch_size=batch_size
    )
