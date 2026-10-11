"""Transactional lifecycle for jointly owned MariaDB job and capacity slot."""
from __future__ import annotations

from mcm_solarcheck.infrastructure.mariadb_job_lease_adapter import _identity, _job_id
from mcm_solarcheck.infrastructure.mariadb_job_lease_sql import validate_lease_seconds
from mcm_solarcheck.infrastructure.mariadb_bounded_lifecycle_sql import (
    LOCK_OWNED_PAIR_SQL, RENEW_PAIR_SQL, COMPLETE_PAIR_SQL,
)


class MariaDBBoundedJobLifecycle:
    def __init__(self, connection_factory):
        if not callable(connection_factory):
            raise TypeError("connection_factory required")
        self.connection_factory = connection_factory

    def _run(self, job_id, worker_id, slot_id, token, *, seconds=None, complete=False):
        _job_id(job_id)
        _identity(worker_id)
        if type(slot_id) is not int or slot_id not in (1, 2):
            raise ValueError("invalid slot")
        if not isinstance(token, str) or len(token) != 32:
            raise ValueError("invalid token")
        if not complete:
            validate_lease_seconds(seconds)
        conn = self.connection_factory()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(LOCK_OWNED_PAIR_SQL, (slot_id, job_id, token, worker_id, token))
                if cursor.fetchone() != (slot_id,):
                    conn.rollback()
                    return False
                if complete:
                    sqls = COMPLETE_PAIR_SQL
                    params = ((job_id, worker_id, token), (slot_id, job_id, token))
                else:
                    sqls = RENEW_PAIR_SQL
                    params = ((seconds, slot_id, job_id, token), (seconds, job_id, worker_id, token))
                for sql, args in zip(sqls, params):
                    cursor.execute(sql, args)
                    if type(cursor.rowcount) is not int or cursor.rowcount != 1:
                        conn.rollback()
                        return False
                conn.commit()
                return True
            finally:
                cursor.close()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def renew(self, job_id, worker_id, slot_id, token, *, lease_seconds=60):
        return self._run(job_id, worker_id, slot_id, token, seconds=lease_seconds)

    def complete(self, job_id, worker_id, slot_id, token):
        return self._run(job_id, worker_id, slot_id, token, complete=True)
