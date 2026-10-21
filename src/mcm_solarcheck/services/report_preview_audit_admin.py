"""Administrator-only, read-only inspection of report-preview interaction events.

The desktop user-facing report services do not expose these bits. The caller
must provide an identity authenticated by the surrounding admin entry point:
this module is an authorization boundary, not a password verifier. Local
SQLite file owners still control their own database; no cryptographic attestation.
"""
from __future__ import annotations
from dataclasses import dataclass

from mcm_solarcheck.services.authorized_grant_administration import GrantAdministrator
from mcm_solarcheck.storage.sqlite import ProjectDatabase


@dataclass(frozen=True)
class AdminReportPreviewAudit:
    approval_id: int
    project_id: str
    report_id: str
    approved_by: str
    approved_at_utc: str
    reached_preview_end: bool | None


class AuthorizedReportPreviewAudit:
    REQUIRED = "report_release:audit_read"

    def __init__(self, database: ProjectDatabase):
        if not isinstance(database, ProjectDatabase):
            raise TypeError("project database required")
        self._database = database

    def inspect(self, identity: GrantAdministrator, project_id: str,
                *, limit: int = 50) -> tuple[AdminReportPreviewAudit, ...]:
        if (
            not isinstance(identity, GrantAdministrator)
            or identity.authenticated is not True
            or not isinstance(identity.actor_id, str)
            or not identity.actor_id.strip()
            or not isinstance(identity.permissions, frozenset)
            or self.REQUIRED not in identity.permissions
        ):
            raise PermissionError("authenticated report audit administrator required")
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project id required")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("audit limit must be between 1 and 100")
        with self._database.connect() as sql:
            if sql.execute(
                "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
            ).fetchone() is None:
                raise KeyError("unknown project")
            records = sql.execute(
                """SELECT r.approval_id,r.project_id,r.report_id,r.approved_by,
                          r.approved_at_utc,a.reached_preview_end
                   FROM report_release_decisions AS r
                   LEFT JOIN report_release_read_audit AS a
                     ON a.approval_id=r.approval_id
                   WHERE r.project_id=?
                   ORDER BY r.approval_id DESC LIMIT ?""",
                (project_id, limit),
            )
            return tuple(
                AdminReportPreviewAudit(
                    row["approval_id"], row["project_id"], row["report_id"],
                    row["approved_by"], row["approved_at_utc"],
                    None if row["reached_preview_end"] is None
                    else bool(row["reached_preview_end"]),
                ) for row in records
            )
