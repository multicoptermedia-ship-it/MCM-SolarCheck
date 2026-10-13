"""Opt-in atomic claim of one MariaDB processing slot and queued job.

Requires an InnoDB connection with autocommit disabled. No automatic
expired-lease recovery or external worker execution.
"""
from __future__ import annotations

import uuid

from mcm_solarcheck.infrastructure.mariadb_job_lease_sql import CLAIM_QUEUED_JOB_SQL, validate_lease_seconds
from mcm_solarcheck.infrastructure.mariadb_processing_slot_sql import (
    LOCK_SLOTS_SQL, RESERVE_FREE_SLOT_SQL, select_free_slot,
)
from mcm_solarcheck.infrastructure.mariadb_job_lease_adapter import _job_id, _identity


class MariaDBBoundedJobAdmission:
    def __init__(self, connection_factory):
        if not callable(connection_factory):
            raise TypeError("connection_factory required")
        self.connection_factory = connection_factory

    def claim(self, job_id, worker_id, *, lease_seconds=60):
        _job_id(job_id)
        _identity(worker_id)
        validate_lease_seconds(lease_seconds)
        connection = self.connection_factory()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(LOCK_SLOTS_SQL)
                slot = select_free_slot(cursor.fetchall())
                if slot is None:
                    connection.rollback()
                    return None
                token = uuid.uuid4().hex
                cursor.execute(RESERVE_FREE_SLOT_SQL, (job_id, token, lease_seconds, slot))
                if cursor.rowcount != 1:
                    connection.rollback()
                    return None
                cursor.execute(CLAIM_QUEUED_JOB_SQL, (worker_id, token, lease_seconds, job_id))
                if cursor.rowcount != 1:
                    connection.rollback()
                    return None
                connection.commit()
                return (slot, token)
            finally:
                cursor.close()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
