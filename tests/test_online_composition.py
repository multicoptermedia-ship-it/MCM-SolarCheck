from __future__ import annotations

import pytest

from mcm_solarcheck.services.compute_jobs import ComputeJobStatus

from mcm_solarcheck.infrastructure.online_persistence import build_online_persistence
from mcm_solarcheck.infrastructure.online_private_paths import OnlinePrivatePaths
from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPSecurity
from mcm_solarcheck.services.invoice_creation import InvoiceRenderConfig
from mcm_solarcheck.services.online_composition import build_online_services
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.payment_provider import PaymentProviderCapabilities, PaymentProviderRegistry


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
        public_base_url="https://app.mcm-solarcheck.de",
        payment_gateway=FakePaymentGateway(),
        sepa_gateway=FakeSepaGateway(),
        sepa_provider_id="provider-a",
        payment_providers=PaymentProviderRegistry((PaymentProviderCapabilities("provider-a", frozenset({PaymentMethod.CARD, PaymentMethod.PAYPAL, PaymentMethod.SEPA_DIRECT_DEBIT})),)),
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



def grant_online_entitlement(persistence, user_id: str) -> None:
    from mcm_solarcheck.services.online_entitlement import OnlineEntitlement, OnlineProduct

    persistence.entitlements.save(
        OnlineEntitlement(user_id, OnlineProduct.FULL, active=True)
    )



def configure_production_commerce(persistence) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence.tariffs.save(
        initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc))
    )
    for account_id, kind in (
        ("merchant-ready-card", MerchantAccountKind.CARD_PROCESSOR),
        ("merchant-ready-paypal", MerchantAccountKind.PAYPAL),
        ("merchant-ready-sepa", MerchantAccountKind.BANK),
    ):
        persistence.merchant_accounts.save(
            MerchantAccount(account_id, "provider-a", kind, account_id)
        )

def test_online_services_fail_closed_without_smtp_secret(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=False)

    with pytest.raises(RuntimeError, match="SMTP password is not configured"):
        online_services(persistence)


def test_online_services_share_authoritative_persistence(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)
    configure_production_commerce(persistence)
    grant_online_entitlement(persistence, "user-a")
    services = online_services(persistence)

    services.compute_jobs.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )
    services.compute_jobs.transition(
        "job-a",
        ComputeJobStatus.RUNNING,
        user_id="user-a",
        project_id="project-a",
    )
    services.compute_jobs.transition(
        "job-a",
        ComputeJobStatus.COMPLETED,
        user_id="user-a",
        project_id="project-a",
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
    assert services.admin_readiness.status().ready is True
    assert services.admin.load().readiness.ready is True
    assert services.admin.load().payment_provider.configured is True
    assert services.admin.load().sepa_provider.configured is True


def test_online_services_compose_projects_from_authoritative_persistence(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)

    created = services.projects.create_project("P-ONLINE", "Online Project")

    assert created.project_id == "P-ONLINE"
    assert services.projects.database is persistence.projects
    assert persistence.projects.project_profile("P-ONLINE") is None
    assert tuple(project.project_id for project in services.projects.projects()) == ("P-ONLINE",)


def test_online_project_and_profile_survive_service_recomposition(tmp_path) -> None:
    from mcm_solarcheck.domain.project_profile import ProjectProfile

    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)
    profile = ProjectProfile(
        customer_name="Solar Kunde",
        site_name="PV Anlage",
        site_street="Testweg 1",
        site_postal_code="50181",
        site_city="Bedburg",
        inspector="MCM",
        site_timezone="Europe/Berlin",
    )

    services.projects.create_project_with_profile(
        "P-RESTART",
        "Persistent Online Project",
        profile,
    )

    recomposed_persistence = setup_persistence(tmp_path, secret_configured=True)
    recomposed_services = online_services(recomposed_persistence)

    assert tuple(
        (project.project_id, project.name)
        for project in recomposed_services.projects.projects()
    ) == (("P-RESTART", "Persistent Online Project"),)
    assert recomposed_services.projects.project_profile("P-RESTART") == profile
    assert recomposed_services.projects.database.path == persistence.projects.path


def test_online_services_require_payment_gateways(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)

    with pytest.raises(TypeError, match="payment_gateway is required"):
        build_online_services(
            persistence,
            invoice_render=invoice_render_config(),
        public_base_url="https://app.mcm-solarcheck.de",
            payment_gateway=None,
            sepa_gateway=FakeSepaGateway(),
            sepa_provider_id="provider-a",
            payment_providers=PaymentProviderRegistry((PaymentProviderCapabilities("provider-a", frozenset({PaymentMethod.CARD, PaymentMethod.PAYPAL, PaymentMethod.SEPA_DIRECT_DEBIT})),)),
        payment_provider_readiness=FakeReadiness(),
            sepa_provider_readiness=FakeReadiness(),
            admin_authorization=AllowAdmin(),
            admin_mutation_guard=AllowMutation(),
        )

    with pytest.raises(TypeError, match="sepa_gateway is required"):
        build_online_services(
            persistence,
            invoice_render=invoice_render_config(),
        public_base_url="https://app.mcm-solarcheck.de",
            payment_gateway=FakePaymentGateway(),
            sepa_gateway=None,
            sepa_provider_id="provider-a",
            payment_providers=PaymentProviderRegistry((PaymentProviderCapabilities("provider-a", frozenset({PaymentMethod.CARD, PaymentMethod.PAYPAL, PaymentMethod.SEPA_DIRECT_DEBIT})),)),
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
        public_base_url="https://app.mcm-solarcheck.de",
            payment_gateway=object(),
            sepa_gateway=FakeSepaGateway(),
            sepa_provider_id="provider-a",
            payment_providers=PaymentProviderRegistry((PaymentProviderCapabilities("provider-a", frozenset({PaymentMethod.CARD, PaymentMethod.PAYPAL, PaymentMethod.SEPA_DIRECT_DEBIT})),)),
        payment_provider_readiness=FakeReadiness(),
            sepa_provider_readiness=FakeReadiness(),
            admin_authorization=AllowAdmin(),
            admin_mutation_guard=AllowMutation(),
        )

    with pytest.raises(TypeError, match=r"sepa_gateway must provide submit\(\)"):
        build_online_services(
            persistence,
            invoice_render=invoice_render_config(),
        public_base_url="https://app.mcm-solarcheck.de",
            payment_gateway=FakePaymentGateway(),
            sepa_gateway=object(),
            sepa_provider_id="provider-a",
            payment_providers=PaymentProviderRegistry((PaymentProviderCapabilities("provider-a", frozenset({PaymentMethod.CARD, PaymentMethod.PAYPAL, PaymentMethod.SEPA_DIRECT_DEBIT})),)),
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
        public_base_url="https://app.mcm-solarcheck.de",
            payment_gateway=FakePaymentGateway(),
            sepa_gateway=FakeSepaGateway(),
            sepa_provider_id="provider-a",
            payment_providers=PaymentProviderRegistry((PaymentProviderCapabilities("provider-a", frozenset({PaymentMethod.CARD, PaymentMethod.PAYPAL, PaymentMethod.SEPA_DIRECT_DEBIT})),)),
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
        public_base_url="https://app.mcm-solarcheck.de",
            payment_gateway=FakePaymentGateway(),
            sepa_gateway=FakeSepaGateway(),
            sepa_provider_id="provider-a",
            payment_providers=PaymentProviderRegistry((PaymentProviderCapabilities("provider-a", frozenset({PaymentMethod.CARD, PaymentMethod.PAYPAL, PaymentMethod.SEPA_DIRECT_DEBIT})),)),
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
    configure_production_commerce(persistence)
    services = online_services(persistence)

    assert services.require_production_ready() is None


def test_online_services_expose_authoritative_compute_job_flow(tmp_path) -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity, ComputeJobStatus

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-e2e")
    services = online_services(persistence)

    created = services.compute_jobs.create(
        job_id="job-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )
    started = services.compute_jobs.start(
        created.job_id,
        user_id="user-e2e",
        project_id="project-e2e",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )

    assert created.status is ComputeJobStatus.QUEUED
    assert started.status is ComputeJobStatus.RUNNING
    assert persistence.compute_jobs.get("job-e2e") == started


def test_online_billing_starts_only_after_completed_compute_job(tmp_path) -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity, ComputeJobStatus

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-e2e")
    services = online_services(persistence)
    services.compute_jobs.create(
        job_id="job-billing-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )
    services.compute_jobs.start(
        "job-billing-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )

    with pytest.raises(ValueError, match="completed compute job"):
        services.billing.create(
            "job-billing-e2e",
            user_id="user-e2e",
            project_id="project-e2e",
        )

    completed = services.compute_jobs.transition(
        "job-billing-e2e",
        ComputeJobStatus.COMPLETED,
        user_id="user-e2e",
        project_id="project-e2e",
    )
    billing = services.billing.create(
        "job-billing-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )

    assert completed.status is ComputeJobStatus.COMPLETED
    assert billing.delivery.job_id == completed.job_id
    assert billing.delivery.export_completed is False
    assert billing.billing_released is False


def test_online_completed_job_delivery_releases_billing_and_allows_capture(tmp_path) -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity
    from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount, PaymentStatus
    from mcm_solarcheck.services.payment_methods import PaymentMethod

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-e2e")
    services = online_services(persistence)
    services.compute_jobs.create(
        job_id="job-delivery-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )
    services.compute_jobs.start(
        "job-delivery-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    services.compute_jobs.transition(
        "job-delivery-e2e",
        ComputeJobStatus.COMPLETED,
        user_id="user-e2e",
        project_id="project-e2e",
    )
    services.billing.create(
        "job-delivery-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )
    services.billing.mark_export_completed(
        "job-delivery-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )
    persistence.reports.path_for("job-delivery-e2e").write_bytes(b"report-e2e")

    persistence.payments.create(
        OnlinePayment(
            "payment-delivery-e2e",
            "user-e2e",
            "project-e2e",
            "job-delivery-e2e",
            PaymentAmount(12900, "EUR"),
            method=PaymentMethod.CARD,
        )
    )
    persistence.payments.authorize(
        "payment-delivery-e2e",
        "user-e2e",
        "project-e2e",
        "provider-payment-reference",
    )

    sent = []
    released = services.report_delivery.deliver(
        "job-delivery-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
        send=sent.append,
    )
    captured = services.payment_capture.capture(
        "payment-delivery-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )

    assert len(sent) == 1
    assert sent[0].content == b"report-e2e"
    assert released.delivery.export_completed is True
    assert released.delivery.report_retrieved is True
    assert released.billing_released is True
    assert captured.status is PaymentStatus.CAPTURED
    assert persistence.payments.get("payment-delivery-e2e") == captured


def test_online_checkout_uses_composed_tariff_merchant_and_payment_state(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.payment import PaymentAmount, PaymentStatus
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    persistence.merchant_accounts.save(
        MerchantAccount(
            "merchant-e2e",
            "provider-a",
            MerchantAccountKind.CARD_PROCESSOR,
            "merchant display",
        )
    )
    persistence.tariffs.save(
        initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc))
    )
    services = online_services(persistence)
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    persistence.billing.create(
        ComputeJobBilling(
            ComputeJobDelivery("job-checkout-e2e", "user-e2e", "project-e2e")
        )
    )

    payment = services.payment_checkout.checkout(
        "payment-checkout-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
        job_id="job-checkout-e2e",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-e2e",
        now=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
    )

    assert payment.status is PaymentStatus.AUTHORIZED
    assert payment.amount == PaymentAmount(14500, "EUR")
    assert payment.tariff_version == 1
    assert payment.merchant_account_id == "merchant-e2e"
    assert payment.merchant_account_version == 1
    assert payment.provider_id == "provider-a"
    assert persistence.payments.get("payment-checkout-e2e") == payment


def test_online_card_checkout_delivery_and_capture_end_to_end(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.payment import PaymentAmount, PaymentStatus
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-e2e")
    persistence.merchant_accounts.save(
        MerchantAccount(
            "merchant-card-e2e",
            "provider-a",
            MerchantAccountKind.CARD_PROCESSOR,
            "merchant display",
        )
    )
    persistence.tariffs.save(
        initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc))
    )
    services = online_services(persistence)

    services.compute_jobs.create(
        job_id="job-card-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )
    services.compute_jobs.start(
        "job-card-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    services.compute_jobs.transition(
        "job-card-e2e",
        ComputeJobStatus.COMPLETED,
        user_id="user-e2e",
        project_id="project-e2e",
    )
    services.billing.create(
        "job-card-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )

    authorized = services.payment_checkout.checkout(
        "payment-card-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
        job_id="job-card-e2e",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-card-e2e",
        now=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
    )
    assert authorized.status is PaymentStatus.AUTHORIZED
    assert authorized.amount == PaymentAmount(14500, "EUR")

    with pytest.raises(ValueError, match="export and report retrieval"):
        services.payment_capture.capture(
            "payment-card-e2e",
            user_id="user-e2e",
            project_id="project-e2e",
        )

    services.billing.mark_export_completed(
        "job-card-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )
    persistence.reports.path_for("job-card-e2e").write_bytes(b"card-e2e-report")
    sent = []
    released = services.report_delivery.deliver(
        "job-card-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
        send=sent.append,
    )
    captured = services.payment_capture.capture(
        "payment-card-e2e",
        user_id="user-e2e",
        project_id="project-e2e",
    )

    assert len(sent) == 1
    assert sent[0].content == b"card-e2e-report"
    assert released.delivery.billable is True
    assert released.billing_released is True
    assert captured.status is PaymentStatus.CAPTURED
    assert captured.tariff_version == 1
    assert captured.plant_kwp == 750
    assert captured.merchant_account_id == "merchant-card-e2e"
    assert captured.provider_id == "provider-a"
    assert persistence.payments.get("payment-card-e2e") == captured


def test_online_registration_is_composed_with_authoritative_persistence(tmp_path, monkeypatch) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.registration import RegistrationStatus

    from mcm_solarcheck.infrastructure.smtp_email import SMTPEmailSender

    sent = []
    monkeypatch.setattr(SMTPEmailSender, "send", lambda self, message: sent.append(message))
    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)
    pending = services.registration.register(
        user_id="user-registration-e2e",
        display_name="SolarCheck Kunde",
        email="kunde@example.com",
        street="Musterweg 1",
        postal_code="50181",
        city="Bedburg",
        now=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
    )

    assert pending.status is RegistrationStatus.PENDING
    persisted = persistence.registrations.get("user-registration-e2e")
    assert persisted == pending
    assert persisted.email == "kunde@example.com"
    assert len(sent) == 1
    assert sent[0].recipient == "kunde@example.com"
    assert "/verify-email?token=" in sent[0].text


def test_online_compute_job_requires_persisted_verified_entitlement(tmp_path, monkeypatch) -> None:
    from datetime import datetime, timezone
    from urllib.parse import parse_qs, urlparse
    from mcm_solarcheck.infrastructure.smtp_email import SMTPEmailSender
    from mcm_solarcheck.services.online_entitlement import OnlineProduct

    sent = []
    monkeypatch.setattr(SMTPEmailSender, "send", lambda self, message: sent.append(message))
    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)

    with pytest.raises(PermissionError, match="entitlement"):
        services.compute_jobs.create(
            job_id="job-before-verification",
            user_id="user-entitled",
            project_id="project-entitled",
        )

    services.registration.register(
        user_id="user-entitled",
        display_name="SolarCheck Kunde",
        email="kunde@example.com",
        street="Musterweg 1",
        postal_code="50181",
        city="Bedburg",
        now=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
    )
    link = next(line for line in sent[0].text.splitlines() if line.startswith("https://"))
    token = parse_qs(urlparse(link).query)["token"][0]
    entitlement = services.registration.verify_and_activate(
        token,
        product=OnlineProduct.TRIAL,
        now=datetime(2026, 10, 2, 12, 1, tzinfo=timezone.utc),
    )

    assert entitlement.active is True
    assert persistence.entitlements.get("user-entitled") == entitlement
    job = services.compute_jobs.create(
        job_id="job-after-verification",
        user_id="user-entitled",
        project_id="project-entitled",
    )
    assert job.user_id == "user-entitled"
    assert persistence.compute_jobs.get("job-after-verification") == job


def test_online_checkout_requires_compute_job_billing_context(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.payment_methods import PaymentMethod
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    persistence.merchant_accounts.save(
        MerchantAccount(
            "merchant-checkout-gate",
            "provider-a",
            MerchantAccountKind.CARD_PROCESSOR,
            "merchant display",
        )
    )
    persistence.tariffs.save(
        initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc))
    )
    services = online_services(persistence)

    with pytest.raises(ValueError, match="compute job billing"):
        services.payment_checkout.checkout(
            "payment-without-billing",
            user_id="user-e2e",
            project_id="project-e2e",
            job_id="missing-job",
            plant_kwp=750,
            method=PaymentMethod.CARD,
            provider_id="provider-a",
            merchant_account_id="merchant-checkout-gate",
            now=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
        )

    with pytest.raises(KeyError):
        persistence.payments.get("payment-without-billing")


def test_online_paypal_checkout_delivery_and_capture_end_to_end(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.payment import PaymentAmount, PaymentStatus
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-paypal-e2e")
    persistence.merchant_accounts.save(
        MerchantAccount(
            "merchant-paypal-e2e",
            "provider-a",
            MerchantAccountKind.PAYPAL,
            "paypal merchant",
        )
    )
    persistence.tariffs.save(
        initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc))
    )
    services = online_services(persistence)

    services.compute_jobs.create(
        job_id="job-paypal-e2e",
        user_id="user-paypal-e2e",
        project_id="project-paypal-e2e",
    )
    services.compute_jobs.start(
        "job-paypal-e2e",
        user_id="user-paypal-e2e",
        project_id="project-paypal-e2e",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    services.compute_jobs.transition(
        "job-paypal-e2e",
        ComputeJobStatus.COMPLETED,
        user_id="user-paypal-e2e",
        project_id="project-paypal-e2e",
    )
    services.billing.create(
        "job-paypal-e2e",
        user_id="user-paypal-e2e",
        project_id="project-paypal-e2e",
    )

    authorized = services.payment_checkout.checkout(
        "payment-paypal-e2e",
        user_id="user-paypal-e2e",
        project_id="project-paypal-e2e",
        job_id="job-paypal-e2e",
        plant_kwp=750,
        method=PaymentMethod.PAYPAL,
        provider_id="provider-a",
        merchant_account_id="merchant-paypal-e2e",
        now=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
    )
    assert authorized.status is PaymentStatus.AUTHORIZED
    assert authorized.amount == PaymentAmount(14500, "EUR")
    assert authorized.method is PaymentMethod.PAYPAL

    with pytest.raises(ValueError, match="export and report retrieval"):
        services.payment_capture.capture(
            "payment-paypal-e2e",
            user_id="user-paypal-e2e",
            project_id="project-paypal-e2e",
        )

    services.billing.mark_export_completed(
        "job-paypal-e2e",
        user_id="user-paypal-e2e",
        project_id="project-paypal-e2e",
    )
    persistence.reports.path_for("job-paypal-e2e").write_bytes(b"paypal-e2e-report")
    sent = []
    released = services.report_delivery.deliver(
        "job-paypal-e2e",
        user_id="user-paypal-e2e",
        project_id="project-paypal-e2e",
        send=sent.append,
    )
    captured = services.payment_capture.capture(
        "payment-paypal-e2e",
        user_id="user-paypal-e2e",
        project_id="project-paypal-e2e",
    )

    assert len(sent) == 1
    assert sent[0].content == b"paypal-e2e-report"
    assert released.delivery.billable is True
    assert released.billing_released is True
    assert captured.status is PaymentStatus.CAPTURED
    assert captured.method is PaymentMethod.PAYPAL
    assert captured.tariff_version == 1
    assert captured.plant_kwp == 750
    assert captured.merchant_account_id == "merchant-paypal-e2e"
    assert captured.provider_id == "provider-a"
    assert persistence.payments.get("payment-paypal-e2e") == captured


def test_online_sepa_checkout_delivery_submission_and_reconciliation_end_to_end(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.payment import PaymentAmount, PaymentStatus
    from mcm_solarcheck.services.sepa import SepaMandate
    from mcm_solarcheck.services.sepa_collection import SepaCollectionStatus
    from mcm_solarcheck.services.sepa_reconciliation import SepaProviderEvent
    from mcm_solarcheck.services.sepa_submission import SepaSubmissionStatus
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-sepa-e2e")
    persistence.merchant_accounts.save(
        MerchantAccount(
            "merchant-sepa-e2e",
            "provider-a",
            MerchantAccountKind.BANK,
            "SEPA settlement account",
        )
    )
    persistence.tariffs.save(
        initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc))
    )
    persistence.sepa_mandates.create(
        SepaMandate("mandate-sepa-e2e", "user-sepa-e2e", "provider-a")
    )
    persistence.sepa_mandates.activate(
        "mandate-sepa-e2e",
        "user-sepa-e2e",
        "provider-mandate-sepa-e2e",
    )
    services = online_services(persistence)

    services.compute_jobs.create(
        job_id="job-sepa-e2e",
        user_id="user-sepa-e2e",
        project_id="project-sepa-e2e",
    )
    services.compute_jobs.start(
        "job-sepa-e2e",
        user_id="user-sepa-e2e",
        project_id="project-sepa-e2e",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    services.compute_jobs.transition(
        "job-sepa-e2e",
        ComputeJobStatus.COMPLETED,
        user_id="user-sepa-e2e",
        project_id="project-sepa-e2e",
    )
    services.billing.create(
        "job-sepa-e2e",
        user_id="user-sepa-e2e",
        project_id="project-sepa-e2e",
    )

    payment = services.sepa_checkout.checkout(
        "payment-sepa-e2e",
        user_id="user-sepa-e2e",
        project_id="project-sepa-e2e",
        job_id="job-sepa-e2e",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-sepa-e2e",
        now=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
    )
    assert payment.status is PaymentStatus.CREATED
    assert payment.method is PaymentMethod.SEPA_DIRECT_DEBIT
    assert payment.amount == PaymentAmount(14500, "EUR")
    assert payment.tariff_version == 1
    assert payment.merchant_account_id == "merchant-sepa-e2e"

    with pytest.raises(ValueError, match="export and report retrieval"):
        services.sepa_payment.submit(
            "payment-sepa-e2e",
            "mandate-sepa-e2e",
            user_id="user-sepa-e2e",
            project_id="project-sepa-e2e",
        )

    services.billing.mark_export_completed(
        "job-sepa-e2e",
        user_id="user-sepa-e2e",
        project_id="project-sepa-e2e",
    )
    persistence.reports.path_for("job-sepa-e2e").write_bytes(b"sepa-e2e-report")
    released = services.report_delivery.deliver(
        "job-sepa-e2e",
        user_id="user-sepa-e2e",
        project_id="project-sepa-e2e",
        send=lambda _report: None,
    )
    provider_reference = services.sepa_payment.submit(
        "payment-sepa-e2e",
        "mandate-sepa-e2e",
        user_id="user-sepa-e2e",
        project_id="project-sepa-e2e",
    )

    submission = persistence.sepa_submissions.get("payment-sepa-e2e")
    collection = persistence.sepa_collections.get("sepa:payment-sepa-e2e")
    reconciled = services.sepa_reconciliation.apply(
        SepaProviderEvent(
            "provider-a",
            provider_reference,
            SepaCollectionStatus.SUCCEEDED,
            event_id="event-sepa-e2e-succeeded",
        )
    )

    assert released.billing_released is True
    assert provider_reference == "provider-sepa-reference"
    assert submission.status is SepaSubmissionStatus.SUBMITTED
    assert collection.status is SepaCollectionStatus.SUBMITTED
    assert reconciled.status is SepaCollectionStatus.SUCCEEDED
    assert persistence.sepa_collections.get("sepa:payment-sepa-e2e").status is SepaCollectionStatus.SUCCEEDED
    assert persistence.payments.get("payment-sepa-e2e") == payment


def test_online_failed_report_delivery_keeps_billing_unreleased_and_payment_authorized(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.payment import PaymentStatus
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-delivery-failure")
    persistence.merchant_accounts.save(
        MerchantAccount(
            "merchant-delivery-failure",
            "provider-a",
            MerchantAccountKind.CARD_PROCESSOR,
            "card merchant",
        )
    )
    persistence.tariffs.save(
        initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc))
    )
    services = online_services(persistence)

    services.compute_jobs.create(
        job_id="job-delivery-failure",
        user_id="user-delivery-failure",
        project_id="project-delivery-failure",
    )
    services.compute_jobs.start(
        "job-delivery-failure",
        user_id="user-delivery-failure",
        project_id="project-delivery-failure",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    services.compute_jobs.transition(
        "job-delivery-failure",
        ComputeJobStatus.COMPLETED,
        user_id="user-delivery-failure",
        project_id="project-delivery-failure",
    )
    services.billing.create(
        "job-delivery-failure",
        user_id="user-delivery-failure",
        project_id="project-delivery-failure",
    )
    authorized = services.payment_checkout.checkout(
        "payment-delivery-failure",
        user_id="user-delivery-failure",
        project_id="project-delivery-failure",
        job_id="job-delivery-failure",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-delivery-failure",
        now=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
    )
    services.billing.mark_export_completed(
        "job-delivery-failure",
        user_id="user-delivery-failure",
        project_id="project-delivery-failure",
    )
    persistence.reports.path_for("job-delivery-failure").write_bytes(
        b"delivery-failure-report"
    )

    def fail_send(_report) -> None:
        raise RuntimeError("delivery transport failed")

    with pytest.raises(RuntimeError, match="delivery transport failed"):
        services.report_delivery.deliver(
            "job-delivery-failure",
            user_id="user-delivery-failure",
            project_id="project-delivery-failure",
            send=fail_send,
        )

    billing = persistence.billing.get("job-delivery-failure")
    payment = persistence.payments.get("payment-delivery-failure")
    assert authorized.status is PaymentStatus.AUTHORIZED
    assert billing.delivery.export_completed is True
    assert billing.delivery.report_retrieved is False
    assert billing.billing_released is False
    assert payment.status is PaymentStatus.AUTHORIZED

    with pytest.raises(ValueError, match="export and report retrieval"):
        services.payment_capture.capture(
            "payment-delivery-failure",
            user_id="user-delivery-failure",
            project_id="project-delivery-failure",
        )


def test_online_composition_requires_explicit_production_activation(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)
    configure_production_commerce(persistence)
    services = online_services(persistence)

    assert services.production.active is False
    with pytest.raises(RuntimeError, match="production operation is not active"):
        services.require_production_active()

    services.activate_production()

    assert services.production.active is True
    services.require_production_active()


def test_online_composition_failed_readiness_cannot_activate_production(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)

    with pytest.raises(RuntimeError, match="pricing"):
        services.activate_production()

    assert services.production.active is False


def test_online_project_pricing_uses_owned_persisted_capacity(tmp_path) -> None:
    from decimal import Decimal
    from mcm_solarcheck.domain.pricing import PriceTier, PricingRule
    from mcm_solarcheck.services.project_creation import CreateProjectRequest
    from mcm_solarcheck.services.project_pricing import ProjectPricingRequest

    persistence = setup_persistence(tmp_path, secret_configured=True)
    pricing_rule = PricingRule(
        version="composition-test",
        tiers=(PriceTier(None, Decimal("500")),),
        vat_rate=Decimal("0.19"),
    )
    services = build_online_services(
        persistence,
        invoice_render=invoice_render_config(),
        public_base_url="https://app.mcm-solarcheck.de",
        payment_gateway=FakePaymentGateway(),
        sepa_gateway=FakeSepaGateway(),
        sepa_provider_id="provider-a",
        payment_providers=PaymentProviderRegistry((PaymentProviderCapabilities("provider-a", frozenset({PaymentMethod.CARD, PaymentMethod.PAYPAL, PaymentMethod.SEPA_DIRECT_DEBIT})),)),
        payment_provider_readiness=FakeReadiness(),
        sepa_provider_readiness=FakeReadiness(),
        admin_authorization=AllowAdmin(),
        admin_mutation_guard=AllowMutation(),
        pricing_rule=pricing_rule,
    )
    services.project_creation.create(
        CreateProjectRequest("user-a", "P-PRICE", "Pricing Project", Decimal("42.5"))
    )

    snapshot = services.project_pricing.price(ProjectPricingRequest("user-a", "P-PRICE"))

    assert snapshot.capacity_kwp == Decimal("42.5")
    assert snapshot.net_total == Decimal("500.00")
    assert snapshot.rule_version == "composition-test"
    with pytest.raises(PermissionError):
        services.project_pricing.price(ProjectPricingRequest("user-b", "P-PRICE"))


def test_online_project_pricing_stays_disabled_without_explicit_rule(tmp_path) -> None:
    persistence = setup_persistence(tmp_path, secret_configured=True)

    assert online_services(persistence).project_pricing is None


def test_online_project_upload_persists_only_for_owned_project(tmp_path) -> None:
    from decimal import Decimal
    from mcm_solarcheck.services.project_creation import CreateProjectRequest
    from mcm_solarcheck.services.project_upload import ProjectUploadRequest

    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)
    services.project_creation.create(
        CreateProjectRequest("user-a", "P-UPLOAD", "Upload Project", Decimal("42.5"))
    )
    content = b"\xff\xd8\xffsolarcheck"
    stored = services.project_upload.upload(
        ProjectUploadRequest(
            "user-a", "P-UPLOAD", "thermal-001.jpg", "image/jpeg", content
        )
    )

    destination = persistence.uploads.project_directory("user-a", "P-UPLOAD") / "thermal-001.jpg"
    assert destination.read_bytes() == content
    assert stored.size_bytes == len(content)

    with pytest.raises(PermissionError):
        services.project_upload.upload(
            ProjectUploadRequest(
                "user-b", "P-UPLOAD", "thermal-002.jpg", "image/jpeg", content
            )
        )


def test_online_processing_recorder_persists_only_matching_compute_job(tmp_path) -> None:
    from decimal import Decimal
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity
    from mcm_solarcheck.services.project_creation import CreateProjectRequest
    from mcm_solarcheck.services.project_processing import (
        ComputeJobProcessingStateRecorder,
        ProjectProcessingState,
    )

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-a")
    services = online_services(persistence)
    services.project_creation.create(
        CreateProjectRequest("user-a", "P-PROCESS", "Processing Project", Decimal("42.5"))
    )
    services.compute_jobs.create(
        job_id="job-process",
        user_id="user-a",
        project_id="P-PROCESS",
    )
    services.compute_jobs.start(
        "job-process",
        user_id="user-a",
        project_id="P-PROCESS",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    recorder = ComputeJobProcessingStateRecorder(
        services.compute_jobs,
        job_id="job-process",
        customer_id="user-a",
        project_id="P-PROCESS",
    )

    recorder("user-a", "P-PROCESS", ProjectProcessingState.RUNNING)
    recorder("user-a", "P-PROCESS", ProjectProcessingState.COMPLETED)

    assert persistence.compute_jobs.get("job-process").status is ComputeJobStatus.COMPLETED

    mismatched = ComputeJobProcessingStateRecorder(
        services.compute_jobs,
        job_id="job-process",
        customer_id="user-b",
        project_id="P-PROCESS",
    )
    with pytest.raises(PermissionError):
        mismatched("user-b", "P-PROCESS", ProjectProcessingState.RUNNING)


def test_composed_online_processing_requires_bound_compute_job(tmp_path) -> None:
    from decimal import Decimal
    from mcm_solarcheck.services.project_creation import CreateProjectRequest
    from mcm_solarcheck.services.project_processing import ProjectProcessingRequest

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-a")
    services = online_services(persistence)
    services.project_creation.create(
        CreateProjectRequest("user-a", "P-BOUND", "Bound Processing", Decimal("42.5"))
    )
    persistence.uploads.project_directory("user-a", "P-BOUND").mkdir(
        parents=True, exist_ok=True
    )

    with pytest.raises(PermissionError, match="not available"):
        services.project_processing.process(
            ProjectProcessingRequest("user-a", "P-BOUND", "missing-job")
        )
