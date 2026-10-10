"""Explicit audited grant service composition for trusted internal callers.

No public route or authentication implementation is provided.
"""
from __future__ import annotations

from mcm_solarcheck.infrastructure.sqlite_audited_recovery_grants import SQLiteAuditedRecoveryGrants
from mcm_solarcheck.infrastructure.read_only_recovery_grants import ReadOnlyRecoveryGrants
from mcm_solarcheck.services.authorized_grant_administration import AuthorizedGrantAdministration
from mcm_solarcheck.services.project_authorized_recovery_service import ProjectAuthorizedRecoveryService


def build_grant_administration(database):
    return AuthorizedGrantAdministration(SQLiteAuditedRecoveryGrants(database))


def build_project_recovery(coordinator, database):
    return ProjectAuthorizedRecoveryService(coordinator, ReadOnlyRecoveryGrants(database))
