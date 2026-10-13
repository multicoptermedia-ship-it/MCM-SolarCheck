"""Read-only inspection of retry lease state; does not claim or renew."""
from __future__ import annotations

from datetime import datetime

from mcm_solarcheck.infrastructure.sqlite_sftp_preflight_retry_leases import _identity, _utc


class SFTPPreflightRetryLeaseInspector:
    def __init__(self, leases):
        self.leases = leases

    def inspect(self, job_id, customer_id, project_id, *, now=None):
        _identity(job_id, customer_id, project_id)
        instant = _utc(now)
        with self.leases._connect() as db:
            row = db.execute(
                """SELECT customer_id, project_id, worker_id, expires_at
                FROM sftp_preflight_retry_leases WHERE job_id=?""", (job_id,)
            ).fetchone()
        if row is None:
            return "not_leased"
        if row[:2] != (customer_id, project_id):
            raise PermissionError("lease ownership mismatch")
        expiry = datetime.fromisoformat(row[3])
        if expiry.tzinfo is None:
            return "invalid_lease"
        return "expired" if instant >= expiry else "active"
