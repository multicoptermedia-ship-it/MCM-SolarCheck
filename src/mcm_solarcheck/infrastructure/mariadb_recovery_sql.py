"""Token-bound recovery SQL; must run in one InnoDB transaction."""
from __future__ import annotations

LOCK_RECOVERY_PAIR_SQL = """SELECT s.slot_id, s.job_id, s.lease_token, s.expires_at,
       j.worker_id, j.lease_token, j.lease_expires_at, j.state
FROM mcm_processing_slots AS s
JOIN mcm_processing_jobs AS j ON j.id=s.job_id
WHERE s.slot_id=%s AND s.job_id=%s AND s.lease_token=%s
FOR UPDATE"""

MARK_RECOVERY_JOB_SQL = """UPDATE mcm_processing_jobs
SET state='queued', worker_id=NULL, lease_token=NULL, lease_expires_at=NULL
WHERE id=%s AND state='running' AND lease_token=%s
  AND lease_expires_at<=UTC_TIMESTAMP(6)"""

RELEASE_RECOVERY_SLOT_SQL = """UPDATE mcm_processing_slots
SET job_id=NULL, lease_token=NULL, expires_at=NULL
WHERE slot_id=%s AND job_id=%s AND lease_token=%s
  AND expires_at<=UTC_TIMESTAMP(6)"""
