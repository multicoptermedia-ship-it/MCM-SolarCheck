"""Offline-only, short-lived in-memory admin sessions and audit facade.

The Qt surface holds only an opaque session handle. It cannot manufacture a
GrantAdministrator identity; this controller constructs it after authenticating
the handle. No credentials are shared with SolarCheck Online or customers.
"""
from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Callable

from mcm_solarcheck.services.authorized_grant_administration import GrantAdministrator
from mcm_solarcheck.services.offline_admin_credentials import (
    verify_offline_admin_credentials, credential_revision, rotate_offline_admin_password,
)
from mcm_solarcheck.services.report_preview_audit_admin import AuthorizedReportPreviewAudit


class OfflineAdminAuditSessions:
    """Permission-scoped, per-process login with expiry and bounded attempts."""

    def __init__(
        self, credential_path: str | Path, audit: AuthorizedReportPreviewAudit,
        *, clock: Callable[[], float] | None = None,
    ):
        if not isinstance(audit, AuthorizedReportPreviewAudit):
            raise TypeError("authorized report audit required")
        self._path = Path(credential_path)
        self._audit = audit
        self._clock = clock or time.monotonic
        self._sessions: dict[str, tuple[str, float, str]] = {}
        self._failed = 0
        self._locked_until = 0.0

    def login(self, actor_id: str, password: str) -> str:
        now = self._clock()
        if now < self._locked_until:
            raise PermissionError("administrator login denied")
        if not verify_offline_admin_credentials(self._path, actor_id, password):
            self._failed += 1
            if self._failed >= 5:
                self._locked_until = now + 60
                self._failed = 0
            raise PermissionError("administrator login denied")
        revision = credential_revision(self._path)
        if revision is None:
            raise PermissionError("administrator login denied")
        self._failed = 0
        token = secrets.token_urlsafe(32)
        self._sessions[token] = (actor_id.strip(), now + 15 * 60, revision)
        return token

    def _require(self, token: str) -> GrantAdministrator:
        if not isinstance(token, str) or not token:
            raise PermissionError("administrator session required")
        session = self._sessions.get(token)
        if session is None:
            raise PermissionError("administrator session required")
        actor_id, expiry, revision = session
        if credential_revision(self._path) != revision:
            self._sessions.pop(token, None)
            raise PermissionError("administrator session invalidated")
        if self._clock() >= expiry:
            self._sessions.pop(token, None)
            raise PermissionError("administrator session expired")
        return GrantAdministrator(
            actor_id, True, frozenset({AuthorizedReportPreviewAudit.REQUIRED}),
        )

    def inspect(self, token: str, project_id: str, *,
                limit: int = 25, offset: int = 0):
        identity = self._require(token)
        return self._audit.inspect(identity, project_id, limit=limit, offset=offset)

    def change_password(self, token: str, current_password: str,
                        new_password: str) -> None:
        """Reauthenticate, rotate atomically, and revoke every local session."""
        identity = self._require(token)
        try:
            rotate_offline_admin_password(
                self._path, identity.actor_id, current_password, new_password,
            )
        except PermissionError:
            self.logout(token)
            raise
        self.revoke_all()

    def logout(self, token: str) -> None:
        if isinstance(token, str):
            self._sessions.pop(token, None)

    def revoke_all(self) -> None:
        self._sessions.clear()
