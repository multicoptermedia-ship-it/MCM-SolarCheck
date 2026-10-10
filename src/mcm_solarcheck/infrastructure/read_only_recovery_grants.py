"""Read-only grant lookup for production recovery authorization.

This adapter deliberately exposes no grant mutation method.
"""
from __future__ import annotations

from mcm_solarcheck.infrastructure.sqlite_audited_recovery_grants import SQLiteAuditedRecoveryGrants


class ReadOnlyRecoveryGrants:
    def __init__(self, database):
        self._store = SQLiteAuditedRecoveryGrants(database)

    def allowed(self, operator_id, customer_id, project_id):
        return self._store.allowed(operator_id, customer_id, project_id)
