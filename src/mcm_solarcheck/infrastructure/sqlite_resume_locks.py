"""Bind resume operations to the existing SQLite lease coordination service.

Only cooperating processes using the same SQLite database are coordinated.
"""
from __future__ import annotations

from mcm_solarcheck.infrastructure.sqlite_upload_leases import SQLiteUploadLeases


class SQLiteResumeLocks:
    def __init__(self, database, *, lease_seconds: float = 60.0):
        self.leases = SQLiteUploadLeases(database, lease_seconds=lease_seconds)

    def hold(self, customer_id: str, project_id: str, transfer_id: str):
        return self.leases.hold(customer_id, project_id, transfer_id)
