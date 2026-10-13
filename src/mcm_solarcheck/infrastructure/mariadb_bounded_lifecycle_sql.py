"""Token-scoped SQL for atomic bounded worker lifecycle."""
from __future__ import annotations

LOCK_OWNED_PAIR_SQL = """SELECT s.slot_id
FROM mcm_processing_slots AS s
JOIN mcm_processing_jobs AS j ON j.id=s.job_id
WHERE s.slot_id=%s AND s.job_id=%s AND s.lease_token=%s
  AND j.worker_id=%s AND j.lease_token=%s AND j.state='running'
  AND s.expires_at>UTC_TIMESTAMP(6)
  AND j.lease_expires_at>UTC_TIMESTAMP(6)
FOR UPDATE"""

RENEW_PAIR_SQL = (
    """UPDATE mcm_processing_slots SET expires_at=DATE_ADD(UTC_TIMESTAMP(6), INTERVAL %s SECOND)
       WHERE slot_id=%s AND job_id=%s AND lease_token=%s AND expires_at>UTC_TIMESTAMP(6)""",
    """UPDATE mcm_processing_jobs SET lease_expires_at=DATE_ADD(UTC_TIMESTAMP(6), INTERVAL %s SECOND)
       WHERE id=%s AND worker_id=%s AND lease_token=%s AND state='running'
         AND lease_expires_at>UTC_TIMESTAMP(6)""",
)

COMPLETE_PAIR_SQL = (
    """UPDATE mcm_processing_jobs SET state='completed', worker_id=NULL,
       lease_token=NULL, lease_expires_at=NULL
       WHERE id=%s AND worker_id=%s AND lease_token=%s AND state='running'
         AND lease_expires_at>UTC_TIMESTAMP(6)""",
    """UPDATE mcm_processing_slots SET job_id=NULL, lease_token=NULL, expires_at=NULL
       WHERE slot_id=%s AND job_id=%s AND lease_token=%s AND expires_at>UTC_TIMESTAMP(6)""",
)
