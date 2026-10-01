from __future__ import annotations

from dataclasses import dataclass

import pytest

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPSecurity
from mcm_solarcheck.services.online_admin import OnlineAdminActions
from mcm_solarcheck.services.online_admin_readiness import OnlineAdminReadinessService
from mcm_solarcheck.services.smtp_admin import (
    SMTPAdminActions,
    SMTPAdminAuditEvent,
    SMTPAdminService,
    SMTPAdminSettingsInput,
)


class Settings:
    def __init__(self):
        self.config = SMTPConfig(
            "smtp.example.invalid",
            465,
            "login",
            security=SMTPSecurity.TLS,
            sender_address="solarcheck@example.invalid",
        )

    def get(self):
        return self.config

    def save(self, config):
        self.config = config


class Secrets:
    def __init__(self):
        self.value = "smtp-secret-sentinel"

    def is_set(self):
        return bool(self.value)

    def replace(self, password):
        self.value = password

    def resolve_for_delivery(self):
        return self.value


class Ready:
    def is_configured(self):
        return True


class Admin:
    def require_admin(self):
        return None


class Mutation:
    def require_mutation_allowed(self):
        return None


@dataclass
class Audit:
    events: list[SMTPAdminAuditEvent]

    def record(self, event):
        self.events.append(event)


def actions():
    settings = Settings()
    secrets = Secrets()
    smtp_service = SMTPAdminService(settings, secrets)
    smtp_actions = SMTPAdminActions(
        smtp_service, Admin(), Mutation(), Audit([])
    )
    readiness = OnlineAdminReadinessService(
        smtp_service, Ready(), Ready()
    )
    return OnlineAdminActions(readiness, smtp_actions, Ready(), Ready()), settings, secrets


def test_online_admin_view_is_secret_free():
    admin, _, secrets = actions()

    view = admin.load()

    assert view.readiness.ready is True
    assert view.smtp.password_is_set is True
    assert view.payment_provider.configured is True
    assert view.sepa_provider.configured is True
    assert secrets.value not in repr(view)
    assert "password" not in view.smtp.__dict__


def test_online_admin_can_save_smtp_settings_without_secret_roundtrip():
    admin, settings, secrets = actions()
    original_secret = secrets.value

    view = admin.save_smtp_settings(
        SMTPAdminSettingsInput(
            "smtp.changed.invalid",
            587,
            "new-login",
            "solarcheck@example.invalid",
            SMTPSecurity.STARTTLS,
        )
    )

    assert settings.config.host == "smtp.changed.invalid"
    assert secrets.value == original_secret
    assert view.smtp.password_is_set is True


def test_online_admin_password_replacement_never_returns_secret():
    admin, _, secrets = actions()

    view = admin.replace_smtp_password("replacement-value")

    assert secrets.value == "replacement-value"
    assert view.smtp.password_is_set is True
    assert "replacement-value" not in repr(view)


def test_online_admin_requires_safe_readiness_boundary():
    with pytest.raises(TypeError, match=r"readiness must provide status\(\)"):
        OnlineAdminActions(
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            Ready(),
            Ready(),
        )


def test_online_admin_requires_secure_smtp_action_boundary():
    class Readiness:
        def status(self):
            raise AssertionError("status must not be called during construction")

    with pytest.raises(TypeError, match=r"smtp must provide load\(\)"):
        OnlineAdminActions(
            Readiness(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            Ready(),
            Ready(),
        )


@pytest.mark.parametrize(
    ("payment", "sepa"),
    ((False, True), (True, False), (False, False)),
)
def test_online_admin_provider_status_exposes_only_boolean_state(payment, sepa):
    class State:
        def __init__(self, configured):
            self.secret = "must-never-be-returned"
            self.configured = configured

        def is_configured(self):
            return self.configured

    settings = Settings()
    secrets = Secrets()
    smtp_service = SMTPAdminService(settings, secrets)
    smtp_actions = SMTPAdminActions(
        smtp_service, Admin(), Mutation(), Audit([])
    )
    payment_state = State(payment)
    sepa_state = State(sepa)
    admin = OnlineAdminActions(
        OnlineAdminReadinessService(
            smtp_service, payment_state, sepa_state
        ),
        smtp_actions,
        payment_state,
        sepa_state,
    )

    view = admin.load()

    assert view.payment_provider.configured is payment
    assert view.sepa_provider.configured is sepa
    assert "must-never-be-returned" not in repr(view)
    assert view.payment_provider.__dict__ == {"configured": payment}
    assert view.sepa_provider.__dict__ == {"configured": sepa}
