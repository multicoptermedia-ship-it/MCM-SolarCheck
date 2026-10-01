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
        smtp_secrets=FakeSecretStore(secret_configured),
    )


class AllowAdmin:
    def require_admin(self) -> None:
        return None


class AllowMutation:
    def require_mutation_allowed(self) -> None:
        return None


class FakePaymentGateway:
    def authorize(self, payment, *, idempotency_key: str):
        from mcm_solarcheck.services.payment_gateway import PaymentAuthorizationResult

        return PaymentAuthorizationResult("provider-payment-reference")

    def capture(self, provider_reference: str, *, idempotency_key: str) -> None:
        pass

    def void(self, provider_reference: str, *, idempotency_key: str) -> None:
        pass


class FakeReadiness:
    def __init__(self, configured: bool = True) -> None:
        self.configured = configured

    def is_configured(self) -> bool:
        return self.configured


class FakeSepaGateway:
    def submit(self, payment, mandate_reference: str, *, idempotency_key: str) -> str:
        return "provider-sepa-reference"


def online_services(persistence, *, payment_ready=True, sepa_ready=True):
    return build_online_services(
        persistence,
        invoice_render=invoice_render_config(),
        payment_gateway=FakePaymentGateway(),
        sepa_gateway=FakeSepaGateway(),
        sepa_provider_id="provider-a",
        payment_provider_readiness=FakeReadiness(payment_ready),
        sepa_provider_readiness=FakeReadiness(sepa_ready),
        admin_authorization=AllowAdmin(),
        admin_mutation_guard=AllowMutation(),
    )


def invoice_render_config():
    return InvoiceRenderConfig(
        ("MCM-Dronetech GmbH",),
        "Zahlung wurde über den gewählten Zahlungsweg ausgeführt.",
    )


def test_online_services_fail_closed_without_smtp_secret(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=False)

    with pytest.raises(RuntimeError, match="SMTP password is not configured"):
        online_services(persistence)


def test_online_services_share_authoritative_persistence(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)

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
    assert services.admin_readiness.status().ready is True
    assert services.admin.load().readiness.ready is True


def test_online_services_require_payment_gateways(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)

    with pytest.raises(TypeError, match="payment_gateway is required"):
        build_online_services(
            persistence,
            invoice_render=invoice_render_config(),
            payment_gateway=None,
            sepa_gateway=FakeSepaGateway(),
            sepa_provider_id="provider-a",
            payment_provider_readiness=FakeReadiness(),
            sepa_provider_readiness=FakeReadiness(),
            admin_authorization=AllowAdmin(),
            admin_mutation_guard=AllowMutation(),
        )

    with pytest.raises(TypeError, match="sepa_gateway is required"):
        build_online_services(
            persistence,
            invoice_render=invoice_render_config(),
            payment_gateway=FakePaymentGateway(),
            sepa_gateway=None,
            sepa_provider_id="provider-a",
            payment_provider_readiness=FakeReadiness(),
            sepa_provider_readiness=FakeReadiness(),
            admin_authorization=AllowAdmin(),
            admin_mutation_guard=AllowMutation(),
        )


def test_online_payment_services_use_durable_operation_state(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)

    assert services.payment_authorization._payments is persistence.payments
    assert services.payment_authorization._gateway is services.payment_capture._gateway
    assert services.payment_authorization._intents is persistence.payment_authorizations
    assert services.payment_capture._payments is persistence.payments
    assert services.payment_capture._billing is persistence.billing
    assert services.payment_capture._operation_intents is persistence.payment_operations
    assert services.payment_void._operation_intents is persistence.payment_operations
    assert services.sepa_payment._submissions is persistence.sepa_submissions
    assert services.sepa_payment._collections is persistence.sepa_collections
    assert services.sepa_payment._billing is persistence.billing


def test_online_services_reject_malformed_payment_gateways(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)

    with pytest.raises(TypeError, match=r"payment_gateway must provide authorize\(\)"):
        build_online_services(
            persistence,
            invoice_render=invoice_render_config(),
            payment_gateway=object(),
            sepa_gateway=FakeSepaGateway(),
            sepa_provider_id="provider-a",
            payment_provider_readiness=FakeReadiness(),
            sepa_provider_readiness=FakeReadiness(),
            admin_authorization=AllowAdmin(),
            admin_mutation_guard=AllowMutation(),
        )

    with pytest.raises(TypeError, match=r"sepa_gateway must provide submit\(\)"):
        build_online_services(
            persistence,
            invoice_render=invoice_render_config(),
            payment_gateway=FakePaymentGateway(),
            sepa_gateway=object(),
            sepa_provider_id="provider-a",
            payment_provider_readiness=FakeReadiness(),
            sepa_provider_readiness=FakeReadiness(),
            admin_authorization=AllowAdmin(),
            admin_mutation_guard=AllowMutation(),
        )


def test_online_services_require_provider_readiness_boundaries(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)

    with pytest.raises(
        TypeError, match=r"payment_provider_readiness must provide is_configured\(\)"
    ):
        build_online_services(
            persistence,
            invoice_render=invoice_render_config(),
            payment_gateway=FakePaymentGateway(),
            sepa_gateway=FakeSepaGateway(),
            sepa_provider_id="provider-a",
            payment_provider_readiness=object(),
            sepa_provider_readiness=FakeReadiness(),
            admin_authorization=AllowAdmin(),
            admin_mutation_guard=AllowMutation(),
        )

    with pytest.raises(
        TypeError, match=r"sepa_provider_readiness must provide is_configured\(\)"
    ):
        build_online_services(
            persistence,
            invoice_render=invoice_render_config(),
            payment_gateway=FakePaymentGateway(),
            sepa_gateway=FakeSepaGateway(),
            sepa_provider_id="provider-a",
            payment_provider_readiness=FakeReadiness(),
            sepa_provider_readiness=object(),
            admin_authorization=AllowAdmin(),
            admin_mutation_guard=AllowMutation(),
        )


def test_online_services_separate_admin_startup_from_production_readiness(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence, payment_ready=False)

    assert services.admin_readiness.status().ready is False
    with pytest.raises(RuntimeError, match="payment_provider"):
        services.require_production_ready()


def test_online_services_allow_explicit_production_readiness(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)

    assert services.require_production_ready() is None
