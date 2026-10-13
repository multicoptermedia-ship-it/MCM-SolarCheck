"""Audited opt-in recovery: mutation and success audit share one transaction."""
from __future__ import annotations

from datetime import datetime, timezone

from mcm_solarcheck.infrastructure.mariadb_expired_lease_inspection import classify_expired_pair
from mcm_solarcheck.infrastructure.mariadb_recovery_sql import (
    LOCK_RECOVERY_PAIR_SQL, MARK_RECOVERY_JOB_SQL, RELEASE_RECOVERY_SLOT_SQL,
)
from mcm_solarcheck.infrastructure.mariadb_recovery_audit_sql import INSERT_RECOVERY_AUDIT_SQL
from mcm_solarcheck.services.mariadb_recovery_authorization import QuiescenceProof


class MariaDBAuditedRecovery:
    def __init__(self, connection_factory, verify_quiescence):
        if not callable(connection_factory) or not callable(verify_quiescence):
            raise TypeError("connection factory and verifier required")
        self.connection_factory = connection_factory
        self.verify_quiescence = verify_quiescence

    def recover(self, proof):
        if not isinstance(proof, QuiescenceProof):
            raise TypeError("QuiescenceProof required")
        if self.verify_quiescence(proof) is not True:
            return False
        connection = self.connection_factory()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(LOCK_RECOVERY_PAIR_SQL, (proof.slot_id, proof.job_id, proof.lease_token))
                row = cursor.fetchone()
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                if classify_expired_pair(row, now) != "expired_requires_quiescence":
                    connection.rollback()
                    return False
                cursor.execute(MARK_RECOVERY_JOB_SQL, (proof.job_id, proof.lease_token))
                if type(cursor.rowcount) is not int or cursor.rowcount != 1:
                    connection.rollback()
                    return False
                cursor.execute(RELEASE_RECOVERY_SLOT_SQL, (proof.slot_id, proof.job_id, proof.lease_token))
                if type(cursor.rowcount) is not int or cursor.rowcount != 1:
                    connection.rollback()
                    return False
                cursor.execute(INSERT_RECOVERY_AUDIT_SQL, (
                    proof.job_id, proof.slot_id, proof.operator_id,
                    proof.evidence_reference, "requeued",
                ))
                if type(cursor.rowcount) is not int or cursor.rowcount != 1:
                    connection.rollback()
                    return False
                connection.commit()
                return True
            finally:
                cursor.close()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
