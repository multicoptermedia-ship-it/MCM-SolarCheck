"""Framework-neutral administrative facade for SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.online_admin_readiness import (
    OnlineAdminReadiness,
    OnlineAdminReadinessService,
)
from mcm_solarcheck.services.smtp_admin import (
    SMTPAdminActions,
    SMTPAdminSettingsInput,
    SMTPAdminView,
    SMTPTestResult,
)


@dataclass(frozen=True)
class OnlineAdminView:
    """UI-safe aggregate; deliberately contains no secret values."""

    readiness: OnlineAdminReadiness
    smtp: SMTPAdminView


class OnlineAdminActions:
    """Small boundary a future HTTPS admin UI can call."""

    def __init__(
        self,
        readiness: OnlineAdminReadinessService,
        smtp: SMTPAdminActions,
    ) -> None:
        for dependency, method, name in (
            (readiness, "status", "readiness"),
            (smtp, "load", "smtp"),
        ):
            if not callable(getattr(dependency, method, None)):
                raise TypeError(f"{name} must provide {method}()")
        self._readiness = readiness
        self._smtp = smtp

    def load(self) -> OnlineAdminView:
        return OnlineAdminView(
            readiness=self._readiness.status(),
            smtp=self._smtp.load(),
        )

    def save_smtp_settings(self, values: SMTPAdminSettingsInput) -> OnlineAdminView:
        self._smtp.save_settings(values)
        return self.load()

    def replace_smtp_password(self, password: str) -> OnlineAdminView:
        self._smtp.replace_password(password)
        return self.load()

    def test_smtp(self) -> SMTPTestResult:
        return self._smtp.send_test_email()
