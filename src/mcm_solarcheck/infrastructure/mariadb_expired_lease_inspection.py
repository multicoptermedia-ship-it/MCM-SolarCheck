"""Read-only SQL for assessing expired MariaDB bounded leases.

No expired slot is automatically freed or reassigned.
"""
from __future__ import annotations

EXPIRED_PAIR_INSPECTION_SQL = """SELECT s.slot_id, s.job_id, s.lease_token,
       s.expires_at, j.worker_id, j.lease_token,
       j.lease_expires_at, j.state
FROM mcm_processing_slots AS s
LEFT JOIN mcm_processing_jobs AS j ON j.id=s.job_id
WHERE s.slot_id=%s AND s.job_id IS NOT NULL
FOR UPDATE"""

def classify_expired_pair(row, now):
    """Classify a locked row; never infer that an external worker has stopped."""
    if row is None:
        return "empty"
    if len(row) != 8:
        raise ValueError("invalid inspection row")
    slot_id, job_id, slot_token, slot_expiry, worker_id, job_token, job_expiry, state = row
    if slot_id not in (1, 2) or job_id is None:
        return "manual_review"
    if not slot_token or not worker_id or slot_token != job_token or state != "running":
        return "manual_review"
    if slot_expiry is None or job_expiry is None:
        return "manual_review"
    if slot_expiry > now and job_expiry > now:
        return "active"
    if slot_expiry <= now and job_expiry <= now:
        return "expired_requires_quiescence"
    return "manual_review"
