"""Pure MariaDB transaction plan for exclusive job admission.

An adapter must execute this inside one database transaction and check rowcount.
No connection, migration, or worker is started here.
"""
from __future__ import annotations

CLAIM_QUEUED_JOB_SQL = """UPDATE mcm_processing_jobs
SET state='running', worker_id=%s, lease_token=%s,
    lease_expires_at=DATE_ADD(UTC_TIMESTAMP(6), INTERVAL %s SECOND)
WHERE id=%s AND state='queued' AND worker_id IS NULL
  AND lease_token IS NULL"""

RENEW_JOB_SQL = """UPDATE mcm_processing_jobs
SET lease_expires_at=GREATEST(
    lease_expires_at, DATE_ADD(UTC_TIMESTAMP(6), INTERVAL %s SECOND)
)
WHERE id=%s AND state='running' AND worker_id=%s
  AND lease_token=%s AND lease_expires_at>UTC_TIMESTAMP(6)"""

COMPLETE_JOB_SQL = """UPDATE mcm_processing_jobs
SET state='completed', worker_id=NULL, lease_token=NULL,
    lease_expires_at=NULL
WHERE id=%s AND state='running' AND worker_id=%s
  AND lease_token=%s AND lease_expires_at>UTC_TIMESTAMP(6)"""


def validate_lease_seconds(value):
    if type(value) is not int or not 1 <= value <= 3600:
        raise ValueError("lease_seconds must be 1..3600")
    return value


def affected_exactly_one(rowcount):
    """A stale worker must never treat a zero-row update as success."""
    if type(rowcount) is not int or rowcount < 0:
        raise ValueError("invalid affected row count")
    return rowcount == 1
