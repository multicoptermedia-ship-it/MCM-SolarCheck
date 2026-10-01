from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.online_persistence import build_online_persistence
from mcm_solarcheck.infrastructure.online_private_paths import OnlinePrivatePaths
from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPSecurity
from mcm_solarcheck.services.invoice_creation import InvoiceRenderConfig
from mcm_solarcheck.services.online_composition import build_online_services


class FakeSecretStore:
    def __init__(self, configured: bool) -> None:
        self.configured = configured

    def is_set(self) -> bool:
        return self.configured

    def replace(self, password: str) -> None:
        self.configured = bool(password)

    def resolve_for_delivery(self) -> str:
        if not self.configured:
            raise RuntimeError("SMTP password is not configured")
        return "test-value"


def setup_persistence(tmp_path, *, secret_configured: bool):
    private = tmp_path / "private"
    paths = OnlinePrivatePaths(
        private / "solarcheck.sqlite",
        private / "reports",
        private / "invoices",
        tmp_path / "public",
    )
    return build_online_persistence(
        paths,
        smtp_default=SMTPConfig(
            "smtp.example.invalid",
            465,
            "solarcheck@example.invalid",
            security=SMTPSecurity.TLS,
        ),
        smtp_secrets=FakeSecretStore(secret_configured),  # type: ignore[arg-type]
    )


def invoice_render_config():
    return InvoiceRenderConfig(
        ("MCM-Dronetech GmbH",),
        "Zahlung wurde über den gewählten Zahlungsweg ausgeführt.",
    )


def test_online_services_fail_closed_without_smtp_secret(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=False)

    with pytest.raises(RuntimeError, match="SMTP password is not configured"):
        build_online_services(
            persistence,
            invoice_render=invoice_render_config(),
        )


def test_online_services_share_authoritative_persistence(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = build_online_services(
        persistence,
        invoice_render=invoice_render_config(),
    )

    services.billing.create(
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert persistence.billing.get("job-a").delivery.job_id == "job-a"
    assert services.report_delivery._billing is persistence.billing
    assert services.report_delivery._reports is persistence.reports
    assert services.payment_execution._sepa_submissions is persistence.sepa_submissions
    assert services.smtp_admin.status().password_is_set is True
