"""Opt-in MariaDB DB-API transaction adapter; driver and connection are injected."""
from __future__ import annotations

import uuid

from mcm_solarcheck.infrastructure.mariadb_job_lease_sql import (
    CLAIM_QUEUED_JOB_SQL, RENEW_JOB_SQL, COMPLETE_JOB_SQL,
    validate_lease_seconds, affected_exactly_one,
)


def _identity(value):
    if not isinstance(value, str) or not value or len(value) > 100:
        raise ValueError("invalid worker identity")
    return value


def _job_id(value):
    if type(value) is not int or value <= 0:
        raise ValueError("job id must be a positive integer")
    return value


class MariaDBJobLeaseAdapter:
    """Each action uses its own transaction and closes its own connection."""

    def __init__(self, connection_factory):
        if not callable(connection_factory):
            raise TypeError("connection_factory required")
        self.connection_factory = connection_factory

    def _execute(self, sql, params):
        connection = self.connection_factory()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, params)
                changed = affected_exactly_one(cursor.rowcount)
                connection.commit()
                return changed
            finally:
                cursor.close()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def claim(self, job_id, worker_id, *, lease_seconds=60):
        _job_id(job_id)
        _identity(worker_id)
        validate_lease_seconds(lease_seconds)
        token = uuid.uuid4().hex
        if self._execute(CLAIM_QUEUED_JOB_SQL, (worker_id, token, lease_seconds, job_id)):
            return token
        return None

    def renew(self, job_id, worker_id, token, *, lease_seconds=60):
        _job_id(job_id)
        _identity(worker_id)
        if not isinstance(token, str) or len(token) != 32:
            raise ValueError("invalid token")
        validate_lease_seconds(lease_seconds)
        return self._execute(RENEW_JOB_SQL, (lease_seconds, job_id, worker_id, token))

    def complete(self, job_id, worker_id, token):
        _job_id(job_id)
        _identity(worker_id)
        if not isinstance(token, str) or len(token) != 32:
            raise ValueError("invalid token")
        return self._execute(COMPLETE_JOB_SQL, (job_id, worker_id, token))
