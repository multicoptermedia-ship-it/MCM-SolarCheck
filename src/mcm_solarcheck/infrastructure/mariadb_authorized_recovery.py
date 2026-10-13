"""Opt-in recovery with externally verified quiescence and transactional fencing."""
from __future__ import annotations

from datetime import datetime, timezone

from mcm_solarcheck.infrastructure.mariadb_expired_lease_inspection import classify_expired_pair
from mcm_solarcheck.infrastructure.mariadb_recovery_sql import (
    LOCK_RECOVERY_PAIR_SQL, MARK_RECOVERY_JOB_SQL, RELEASE_RECOVERY_SLOT_SQL,
)
from mcm_solarcheck.services.mariadb_recovery_authorization import QuiescenceProof


class MariaDBAuthorizedRecovery:
    def __init__(self, connection_factory, verify_quiescence):
        if not callable(connection_factory) or not callable(verify_quiescence):
            raise TypeError("connection factory and external verifier required")
        self.connection_factory = connection_factory
        self.verify_quiescence = verify_quiescence

    def recover(self, proof):
        if not isinstance(proof, QuiescenceProof):
            raise TypeError("QuiescenceProof required")
        # Verifier must establish that the old worker cannot publish or write.
        if self.verify_quiescence(proof) is not True:
            return False
        conn = self.connection_factory()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(LOCK_RECOVERY_PAIR_SQL, (proof.slot_id, proof.job_id, proof.lease_token))
                row = cursor.fetchone()
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                if classify_expired_pair(row, now) != "expired_requires_quiescence":
                    conn.rollback()
                    return False
                cursor.execute(MARK_RECOVERY_JOB_SQL, (proof.job_id, proof.lease_token))
                if type(cursor.rowcount) is not int or cursor.rowcount != 1:
                    conn.rollback()
                    return False
                cursor.execute(RELEASE_RECOVERY_SLOT_SQL, (proof.slot_id, proof.job_id, proof.lease_token))
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
