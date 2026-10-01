import pytest

from __future__ import annotations

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPSecurity
from mcm_solarcheck.services.online_admin_readiness import OnlineAdminReadinessService
from mcm_solarcheck.services.smtp_admin import SMTPAdminService


class Settings:
    def get(self):
        return SMTPConfig(
            "smtp.example.invalid",
            465,
            "solarcheck@example.invalid",
            security=SMTPSecurity.TLS,
        )

    def save(self, config):
        pass


class Secrets:
    def __init__(self, configured: bool):
        self.configured = configured

    def is_set(self):
        return self.configured

    def replace(self, password):
        self.configured = bool(password)

    def resolve_for_delivery(self):
        raise AssertionError("readiness must never resolve SMTP secrets")


class Readiness:
    def __init__(self, configured: bool):
        self.configured = configured

    def is_configured(self):
        return self.configured


def service(*, smtp=True, payment=True, sepa=True):
    return OnlineAdminReadinessService(
        SMTPAdminService(Settings(), Secrets(smtp)),
        Readiness(payment),
        Readiness(sepa),
    )


def test_online_admin_readiness_reports_only_configuration_state():
    status = service().status()

    assert status.ready is True
    assert status.smtp_configured is True
    assert status.payment_provider_configured is True
    assert status.sepa_provider_configured is True
    assert not hasattr(status, "password")
    assert not hasattr(status, "account")


def test_online_admin_readiness_fails_closed_for_each_missing_backend():
    assert service(smtp=False).status().ready is False
    assert service(payment=False).status().ready is False
    assert service(sepa=False).status().ready is False


def test_online_admin_readiness_requires_safe_status_boundaries():
    try:
        OnlineAdminReadinessService(
            object(),
            Readiness(True),
            Readiness(True),
        )
    except TypeError as exc:
        assert "smtp must provide status()" in str(exc)
    else:
        raise AssertionError("malformed SMTP admin service must be rejected")


def test_require_ready_returns_secret_free_status_when_complete():
    status = service().require_ready()
    assert status.ready is True
    assert not hasattr(status, "password")
    assert not hasattr(status, "account")


@pytest.mark.parametrize(
    ("kwargs", "missing"),
    (
        ({"smtp": False}, "smtp"),
        ({"payment": False}, "payment_provider"),
        ({"sepa": False}, "sepa_provider"),
    ),
)
def test_require_ready_fails_closed_with_missing_component(kwargs, missing):
    with pytest.raises(RuntimeError, match=missing):
        service(**kwargs).require_ready()


def test_require_ready_reports_all_missing_components():
    with pytest.raises(
        RuntimeError,
        match=r"smtp, payment_provider, sepa_provider",
    ):
        service(smtp=False, payment=False, sepa=False).require_ready()
