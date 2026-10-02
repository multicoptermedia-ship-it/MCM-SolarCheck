"""Secret-free administrative readiness for SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mcm_solarcheck.services.smtp_admin import SMTPAdminService


@dataclass(frozen=True)
class ConfigurationStatus:
    """UI-safe provider state containing no identifier or credential value."""

    configured: bool


class ConfigurationReadiness(Protocol):
    """Deployment-owned readiness without exposing credentials or account data."""

    def is_configured(self) -> bool:
        ...

    def status(self) -> ConfigurationStatus:
        return ConfigurationStatus(configured=_configured(self))


def _configured(readiness: ConfigurationReadiness) -> bool:
    """Fail closed when a readiness adapter violates its boolean contract."""
    configured = readiness.is_configured()
    if type(configured) is not bool:
        raise TypeError("is_configured() must return bool")
    return configured


@dataclass(frozen=True)
class OnlineAdminReadiness:
    smtp_configured: bool
    payment_provider_configured: bool
    sepa_provider_configured: bool
    pricing_configured: bool
    merchant_accounts_configured: bool

    @property
    def ready(self) -> bool:
        return (
            self.smtp_configured
            and self.payment_provider_configured
            and self.sepa_provider_configured
            and self.pricing_configured
            and self.merchant_accounts_configured
        )


class OnlineAdminReadinessService:
    """Build a UI-safe readiness view; never return secret or account values."""

    def __init__(
        self,
        smtp: SMTPAdminService,
        payment_provider: ConfigurationReadiness,
        sepa_provider: ConfigurationReadiness,
        pricing: ConfigurationReadiness,
        merchant_accounts: ConfigurationReadiness,
    ) -> None:
        for dependency, method, name in (
            (smtp, "status", "smtp"),
            (payment_provider, "is_configured", "payment_provider"),
            (sepa_provider, "is_configured", "sepa_provider"),
            (pricing, "is_configured", "pricing"),
            (merchant_accounts, "is_configured", "merchant_accounts"),
        ):
            if not callable(getattr(dependency, method, None)):
                raise TypeError(f"{name} must provide {method}()")
        self._smtp = smtp
        self._payment_provider = payment_provider
        self._sepa_provider = sepa_provider
        self._pricing = pricing
        self._merchant_accounts = merchant_accounts

    def require_ready(self) -> OnlineAdminReadiness:
        """Fail closed before enabling commercial online operation."""
        status = self.status()
        missing = []
        if not status.smtp_configured:
            missing.append("smtp")
        if not status.payment_provider_configured:
            missing.append("payment_provider")
        if not status.sepa_provider_configured:
            missing.append("sepa_provider")
        if not status.pricing_configured:
            missing.append("pricing")
        if not status.merchant_accounts_configured:
            missing.append("merchant_accounts")
        if missing:
            raise RuntimeError(
                "online services are not production-ready: " + ", ".join(missing)
            )
        return status

    def status(self) -> OnlineAdminReadiness:
        smtp = self._smtp.status()
        smtp_configured = bool(
            smtp.host
            and smtp.port > 0
            and smtp.username
            and smtp.sender_address
            and smtp.password_is_set
        )
        return OnlineAdminReadiness(
            smtp_configured=smtp_configured,
            payment_provider_configured=_configured(self._payment_provider),
            sepa_provider_configured=_configured(self._sepa_provider),
            pricing_configured=_configured(self._pricing),
            merchant_accounts_configured=_configured(self._merchant_accounts),
        )
