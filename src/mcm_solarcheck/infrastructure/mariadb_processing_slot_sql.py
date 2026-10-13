"""Pure SQL contracts for two database-owned processing slots.

Slot allocation and job transition must run in one transaction, with
serialization and rollback; these statements alone do not enforce capacity.
"""
from __future__ import annotations

LOCK_SLOTS_SQL = """SELECT slot_id, job_id, expires_at
FROM mcm_processing_slots ORDER BY slot_id FOR UPDATE"""

RESERVE_FREE_SLOT_SQL = """UPDATE mcm_processing_slots
SET job_id=%s, lease_token=%s,
    expires_at=DATE_ADD(UTC_TIMESTAMP(6), INTERVAL %s SECOND)
WHERE slot_id=%s AND job_id IS NULL AND lease_token IS NULL"""

RENEW_SLOT_SQL = """UPDATE mcm_processing_slots
SET expires_at=GREATEST(
    expires_at, DATE_ADD(UTC_TIMESTAMP(6), INTERVAL %s SECOND)
)
WHERE slot_id=%s AND job_id=%s AND lease_token=%s
  AND expires_at>UTC_TIMESTAMP(6)"""

RELEASE_SLOT_SQL = """UPDATE mcm_processing_slots
SET job_id=NULL, lease_token=NULL, expires_at=NULL
WHERE slot_id=%s AND job_id=%s AND lease_token=%s"""


def select_free_slot(locked_rows):
    """Only empty rows are free; expired occupied slots require separate recovery."""
    rows = list(locked_rows)
    ids = [row[0] for row in rows]
    if ids != [1, 2]:
        raise ValueError("both processing slots must be locked in order")
    for slot_id, job_id, expiry in rows:
        if job_id is None:
            return slot_id
    return None
