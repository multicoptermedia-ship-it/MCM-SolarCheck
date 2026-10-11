"""Read-only bounded lease recovery assessment using injected DB-API connections."""
from __future__ import annotations

from datetime import datetime, timezone

from mcm_solarcheck.infrastructure.mariadb_expired_lease_inspection import (
    EXPIRED_PAIR_INSPECTION_SQL, classify_expired_pair,
)


class MariaDBExpiredLeaseInspector:
    def __init__(self, connection_factory):
        if not callable(connection_factory):
            raise TypeError("connection_factory required")
        self.connection_factory = connection_factory

    def inspect(self, slot_id, *, now=None):
        if type(slot_id) is not int or slot_id not in (1, 2):
            raise ValueError("invalid slot")
        if now is None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not isinstance(now, datetime) or now.tzinfo is not None:
            raise ValueError("now must be a naive UTC datetime")
        conn = self.connection_factory()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(EXPIRED_PAIR_INSPECTION_SQL, (slot_id,))
                row = cursor.fetchone()
                status = classify_expired_pair(row, now)
                conn.rollback()
                return status
            finally:
                cursor.close()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()
