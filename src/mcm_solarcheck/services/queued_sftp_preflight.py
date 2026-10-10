"""Opt-in read-only SFTP preflight for durable queued project identities.

This is a separate pre-dispatch inspection step; it does not admit compute jobs.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.queued_job_dispatcher import PendingProjectJob
from mcm_solarcheck.services.sftp_project_session_manager import SFTPProjectContext
from mcm_solarcheck.services.sftp_project_paths import project_sftp_directory


@dataclass(frozen=True)
class QueuedSFTPInspection:
    job_id: str
    customer_id: str
    project_id: str
    directory_exists: bool


class QueuedSFTPPreflight:
    def __init__(self, sessions):
        self._sessions = sessions

    def inspect(self, job: PendingProjectJob) -> QueuedSFTPInspection:
        if not isinstance(job, PendingProjectJob):
            raise TypeError("PendingProjectJob required")
        context = SFTPProjectContext(job.customer_id, job.project_id)
        with self._sessions.lease(context) as session:
            path = project_sftp_directory(session.root, context.customer_id, context.project_id)
            exists = session.directory_exists(context, path)
        return QueuedSFTPInspection(
            job_id=job.job_id,
            customer_id=context.customer_id,
            project_id=context.project_id,
            directory_exists=exists,
        )
