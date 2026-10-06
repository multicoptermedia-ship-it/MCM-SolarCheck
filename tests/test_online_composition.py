from __future__ import annotations

import pytest

from mcm_solarcheck.services.compute_jobs import ComputeJobStatus

from mcm_solarcheck.infrastructure.online_persistence import build_online_persistence
from mcm_solarcheck.infrastructure.online_private_paths import OnlinePrivatePaths
from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPSecurity
from mcm_solarcheck.services.invoice_creation import InvoiceRenderConfig
from mcm_solarcheck.services.online_composition import build_online_services
from mcm_solarcheck.services.project_processing import ProjectProcessingState
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
    assert persistence.introductory_offers.has_used("user-sepa-e2e") is False
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



def test_composed_online_processing_uses_configured_claim_lease(tmp_path) -> None:
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    from mcm_solarcheck.services.compute_jobs import ComputeCapacity, ComputeJobLease
    from mcm_solarcheck.services.project_creation import CreateProjectRequest
    from mcm_solarcheck.services.project_processing import (
        ProjectProcessingRequest,
        ProjectProcessingState,
    )

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-a")
    lease = ComputeJobLease(
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration=timedelta(minutes=5),
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
        project_processing_lease=lambda: lease,
    )
    services.project_creation.create(
        CreateProjectRequest("user-a", "P-LEASE", "Leased Processing", Decimal("42.5"))
    )
    persistence.uploads.project_directory("user-a", "P-LEASE").mkdir(
        parents=True, exist_ok=True
    )
    services.compute_jobs.create(
        job_id="job-lease",
        user_id="user-a",
        project_id="P-LEASE",
    )
    services.compute_jobs.start(
        "job-lease",
        user_id="user-a",
        project_id="P-LEASE",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    recorder = services.project_processing._record_state_for_request(
        ProjectProcessingRequest("user-a", "P-LEASE", "job-lease")
    )

    recorder("user-a", "P-LEASE", ProjectProcessingState.RUNNING)

    import sqlite3

    with sqlite3.connect(persistence.compute_jobs.database) as connection:
        worker_id, lease_expires_at = connection.execute(
            """
            SELECT worker_id, lease_expires_at
            FROM compute_jobs
            WHERE job_id = ?
            """,
            ("job-lease",),
        ).fetchone()

    assert worker_id is not None
    assert lease_expires_at == lease.expires_at.isoformat()

def test_composed_online_processing_completes_started_job_for_empty_import(tmp_path) -> None:
    from decimal import Decimal
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity
    from mcm_solarcheck.services.project_creation import CreateProjectRequest
    from mcm_solarcheck.services.project_processing import ProjectProcessingRequest

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-a")
    services = online_services(persistence)
    services.project_creation.create(
        CreateProjectRequest("user-a", "P-FAIL", "Failing Processing", Decimal("42.5"))
    )
    persistence.uploads.project_directory("user-a", "P-FAIL").mkdir(
        parents=True, exist_ok=True
    )
    services.compute_jobs.create(
        job_id="job-fail",
        user_id="user-a",
        project_id="P-FAIL",
    )
    services.compute_jobs.start(
        "job-fail",
        user_id="user-a",
        project_id="P-FAIL",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )

    result = services.project_processing.process(
        ProjectProcessingRequest("user-a", "P-FAIL", "job-fail")
    )

    assert result.imported_thermal_frames == 0
    assert result.paired_frames == 0
    assert result.import_failures == 0
    assert persistence.compute_jobs.get("job-fail").status is ComputeJobStatus.COMPLETED


def test_composed_online_processing_renews_lease_during_rgb_import(tmp_path) -> None:
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    import sqlite3

    from mcm_solarcheck.services.compute_jobs import ComputeCapacity, ComputeJobLease
    from mcm_solarcheck.services.project_creation import CreateProjectRequest
    from mcm_solarcheck.services.project_processing import ProjectProcessingRequest

    persistence = setup_persistence(tmp_path, secret_configured=True)
    grant_online_entitlement(persistence, "user-a")
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    leases = iter((
        ComputeJobLease(start, timedelta(minutes=5)),
        ComputeJobLease(start + timedelta(minutes=1), timedelta(minutes=5)),
        ComputeJobLease(start + timedelta(minutes=2), timedelta(minutes=5)),
        ComputeJobLease(start + timedelta(minutes=3), timedelta(minutes=5)),
    ))
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
        project_processing_lease=lambda: next(leases),
    )
    services.project_creation.create(CreateProjectRequest("user-a", "P-RENEW", "Renew Processing", Decimal("42.5")))
    upload = persistence.uploads.project_directory("user-a", "P-RENEW")
    upload.mkdir(parents=True, exist_ok=True)
    jpeg = (
        bytes.fromhex("ffd8ffc00011080bb80fa0")
        + bytes(10)
        + b'<?xpacket begin=""?><x:xmpmeta Make="DJI"></x:xmpmeta>'
    )
    (upload / "DJI_20250825_0001_V.JPG").write_bytes(jpeg)
    services.compute_jobs.create(job_id="job-renew", user_id="user-a", project_id="P-RENEW")
    services.compute_jobs.start("job-renew", user_id="user-a", project_id="P-RENEW", capacity=ComputeCapacity(max_parallel_jobs=1))

    result = services.project_processing.process(
        ProjectProcessingRequest("user-a", "P-RENEW", "job-renew")
    )

    with sqlite3.connect(persistence.compute_jobs.database) as connection:
        status, lease_expires_at = connection.execute(
            "SELECT status, lease_expires_at FROM compute_jobs WHERE job_id = ?",
            ("job-renew",),
        ).fetchone()

    assert result.state is ProjectProcessingState.COMPLETED
    assert result.imported_thermal_frames == 0
    assert status == ComputeJobStatus.COMPLETED.value
    assert lease_expires_at == (start + timedelta(minutes=7)).isoformat()

def test_online_project_pricing_cannot_claim_configured_discount(tmp_path) -> None:
    from decimal import Decimal
    from mcm_solarcheck.domain.pricing import PriceTier, PricingRule
    from mcm_solarcheck.services.project_creation import CreateProjectRequest
    from mcm_solarcheck.services.project_pricing import ProjectPricingRequest

    persistence = setup_persistence(tmp_path, secret_configured=True)
    pricing_rule = PricingRule(
        version="discount-boundary-test",
        tiers=(PriceTier(None, Decimal("500")),),
        planner_discount_rate=Decimal("0.10"),
        maximum_discount_rate=Decimal("0.10"),
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
        CreateProjectRequest("user-a", "P-DISCOUNT", "Discount Boundary", Decimal("50"))
    )

    with pytest.raises(TypeError):
        ProjectPricingRequest("user-a", "P-DISCOUNT", planner_verified=True)

    snapshot = services.project_pricing.price(
        ProjectPricingRequest("user-a", "P-DISCOUNT")
    )
    assert snapshot.discount_rate == Decimal("0")
    assert snapshot.net_total == Decimal("500.00")


def test_verified_customer_gets_intro_price_once_then_regular_tariff(tmp_path) -> None:
    from datetime import datetime, timedelta, timezone
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.payment import PaymentAmount
    from mcm_solarcheck.services.registration import OnlineRegistration
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    now = datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc)
    pending = OnlineRegistration(
        "user-intro-e2e",
        "Intro Customer",
        "intro@example.com",
        street="Musterweg 1",
        postal_code="50181",
        city="Bedburg",
    )
    persistence.registrations.create(
        pending,
        token="intro-token",
        expires_at=now + timedelta(minutes=30),
    )
    persistence.registrations.verify("intro-token", now=now)
    persistence.merchant_accounts.save(
        MerchantAccount(
            "merchant-intro-e2e",
            "provider-a",
            MerchantAccountKind.CARD_PROCESSOR,
            "merchant display",
        )
    )
    persistence.tariffs.save(initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc)))
    services = online_services(persistence)

    from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus
    for suffix in ("first", "second"):
        persistence.compute_jobs.create(ComputeJob(f"job-intro-{suffix}", "user-intro-e2e", f"project-intro-{suffix}", ComputeJobStatus.COMPLETED))

    for suffix in ("first", "second"):
        persistence.billing.create(
            ComputeJobBilling(
                ComputeJobDelivery(
                    f"job-intro-{suffix}",
                    "user-intro-e2e",
                    f"project-intro-{suffix}",
                )
            )
        )

    first = services.payment_checkout.checkout(
        "payment-intro-first",
        user_id="user-intro-e2e",
        project_id="project-intro-first",
        job_id="job-intro-first",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-intro-e2e",
        now=now,
    )
    assert first.amount == PaymentAmount(5900, "EUR")

    services.billing.mark_export_completed(
        "job-intro-first",
        user_id="user-intro-e2e",
        project_id="project-intro-first",
    )
    services.billing.mark_report_retrieved(
        "job-intro-first",
        user_id="user-intro-e2e",
        project_id="project-intro-first",
    )
    services.billing.release(
        "job-intro-first",
        user_id="user-intro-e2e",
        project_id="project-intro-first",
    )
    services.payment_capture.capture(
        "payment-intro-first",
        user_id="user-intro-e2e",
        project_id="project-intro-first",
    )
    assert persistence.introductory_offers.has_used("user-intro-e2e") is True

    second = services.payment_checkout.checkout(
        "payment-intro-second",
        user_id="user-intro-e2e",
        project_id="project-intro-second",
        job_id="job-intro-second",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-intro-e2e",
        now=now,
    )
    assert second.amount == PaymentAmount(14500, "EUR")
    assert persistence.introductory_offers.has_used("user-intro-e2e") is True


def test_verified_sepa_checkout_uses_introductory_price(tmp_path) -> None:
    from datetime import datetime, timedelta, timezone
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.payment import PaymentAmount
    from mcm_solarcheck.services.registration import OnlineRegistration
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    now = datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc)
    persistence.registrations.create(
        OnlineRegistration("user-sepa-intro", "SEPA Intro", "sepa-intro@example.com"),
        token="sepa-intro-token",
        expires_at=now + timedelta(minutes=30),
    )
    persistence.registrations.verify("sepa-intro-token", now=now)
    persistence.merchant_accounts.save(
        MerchantAccount("merchant-sepa-intro", "provider-a", MerchantAccountKind.BANK, "SEPA")
    )
    persistence.tariffs.save(initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc)))
    persistence.billing.create(
        ComputeJobBilling(ComputeJobDelivery("job-sepa-intro", "user-sepa-intro", "project-sepa-intro"))
    )
    services = online_services(persistence)

    payment = services.sepa_checkout.checkout(
        "payment-sepa-intro",
        user_id="user-sepa-intro",
        project_id="project-sepa-intro",
        job_id="job-sepa-intro",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-sepa-intro",
        now=now,
    )

    assert payment.amount == PaymentAmount(5900, "EUR")
    assert persistence.introductory_offers.has_used("user-sepa-intro") is False


def _verified_sepa_intro_services(tmp_path, user_id):
    from datetime import datetime, timedelta, timezone
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.registration import OnlineRegistration
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    now = datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc)
    persistence.registrations.create(
        OnlineRegistration(user_id, "SEPA Intro", user_id + "@example.com"),
        token=user_id + "-token",
        expires_at=now + timedelta(minutes=30),
    )
    persistence.registrations.verify(user_id + "-token", now=now)
    persistence.merchant_accounts.save(
        MerchantAccount("merchant-" + user_id, "provider-a", MerchantAccountKind.BANK, "SEPA")
    )
    persistence.tariffs.save(initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc)))
    persistence.billing.create(
        ComputeJobBilling(ComputeJobDelivery("job-" + user_id, user_id, "project-" + user_id))
    )
    return persistence, online_services(persistence), now


def test_failed_sepa_merchant_binding_releases_introductory_offer(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-bind")

    with pytest.raises(KeyError):
        services.sepa_checkout.checkout(
            "payment-sepa-bind",
            user_id="user-sepa-bind",
            project_id="project-user-sepa-bind",
            job_id="job-user-sepa-bind",
            plant_kwp=750,
            provider_id="provider-a",
            merchant_account_id="missing-merchant",
            now=now,
        )

    assert persistence.introductory_offers.reserve(
        "user-sepa-bind", "payment-sepa-bind-retry", policy_version=1, now=now
    )


def test_failed_sepa_snapshot_binding_releases_introductory_offer(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-snapshot")

    def fail_snapshot(*args, **kwargs):
        raise RuntimeError("SEPA snapshot binding failed")

    services.sepa_checkout._payments.bind_processing_snapshot = fail_snapshot

    with pytest.raises(RuntimeError, match="SEPA snapshot binding failed"):
        services.sepa_checkout.checkout(
            "payment-sepa-snapshot",
            user_id="user-sepa-snapshot",
            project_id="project-user-sepa-snapshot",
            job_id="job-user-sepa-snapshot",
            plant_kwp=750,
            provider_id="provider-a",
            merchant_account_id="merchant-user-sepa-snapshot",
            now=now,
        )

    assert persistence.introductory_offers.reserve(
        "user-sepa-snapshot", "payment-sepa-snapshot-retry", policy_version=1, now=now
    )


def test_sepa_checkout_retry_keeps_introductory_price(tmp_path) -> None:
    from mcm_solarcheck.services.payment import PaymentAmount

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-retry")
    assert persistence.introductory_offers.reserve(
        "user-sepa-retry", "payment-sepa-retry", policy_version=1, now=now
    )

    payment = services.sepa_checkout.checkout(
        "payment-sepa-retry",
        user_id="user-sepa-retry",
        project_id="project-user-sepa-retry",
        job_id="job-user-sepa-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-retry",
        now=now,
    )

    assert payment.amount == PaymentAmount(5900, "EUR")


def test_failed_sepa_retry_releases_existing_same_payment_reservation(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-failed-retry")
    assert persistence.introductory_offers.reserve(
        "user-sepa-failed-retry", "payment-sepa-failed-retry", policy_version=1, now=now
    )

    def fail_snapshot(*args, **kwargs):
        raise RuntimeError("SEPA retry snapshot failed")

    services.sepa_checkout._payments.bind_processing_snapshot = fail_snapshot

    with pytest.raises(RuntimeError, match="SEPA retry snapshot failed"):
        services.sepa_checkout.checkout(
            "payment-sepa-failed-retry",
            user_id="user-sepa-failed-retry",
            project_id="project-user-sepa-failed-retry",
            job_id="job-user-sepa-failed-retry",
            plant_kwp=750,
            provider_id="provider-a",
            merchant_account_id="merchant-user-sepa-failed-retry",
            now=now,
        )

    assert persistence.introductory_offers.reserve(
        "user-sepa-failed-retry",
        "payment-sepa-after-failed-retry",
        policy_version=1,
        now=now,
    )


def test_sepa_checkout_retry_keeps_reserved_offer_after_deadline(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.payment import PaymentAmount

    persistence, services, _ = _verified_sepa_intro_services(tmp_path, "user-sepa-deadline")
    reserved_at = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    assert persistence.introductory_offers.reserve(
        "user-sepa-deadline", "payment-sepa-deadline", policy_version=1, now=reserved_at
    )

    payment = services.sepa_checkout.checkout(
        "payment-sepa-deadline",
        user_id="user-sepa-deadline",
        project_id="project-user-sepa-deadline",
        job_id="job-user-sepa-deadline",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-deadline",
        now=datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc),
    )

    assert payment.amount == PaymentAmount(5900, "EUR")


def test_verified_sepa_checkout_after_deadline_uses_regular_price(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.payment import PaymentAmount

    persistence, services, _ = _verified_sepa_intro_services(tmp_path, "user-sepa-expired")

    payment = services.sepa_checkout.checkout(
        "payment-sepa-expired",
        user_id="user-sepa-expired",
        project_id="project-user-sepa-expired",
        job_id="job-user-sepa-expired",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-expired",
        now=datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc),
    )

    assert payment.amount == PaymentAmount(14500, "EUR")
    assert not persistence.introductory_offers.is_reserved(
        "user-sepa-expired", "payment-sepa-expired", policy_version=1
    )


def test_sepa_reserved_offer_is_not_reused_by_different_payment_id(tmp_path) -> None:
    from mcm_solarcheck.services.payment import PaymentAmount

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-other-payment")
    assert persistence.introductory_offers.reserve(
        "user-sepa-other-payment", "payment-sepa-original", policy_version=1, now=now
    )

    payment = services.sepa_checkout.checkout(
        "payment-sepa-other",
        user_id="user-sepa-other-payment",
        project_id="project-user-sepa-other-payment",
        job_id="job-user-sepa-other-payment",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-other-payment",
        now=now,
    )

    assert payment.amount == PaymentAmount(14500, "EUR")
    assert persistence.introductory_offers.is_reserved(
        "user-sepa-other-payment", "payment-sepa-original", policy_version=1
    )


def test_sepa_reserved_offer_is_not_reused_by_different_policy_version(tmp_path) -> None:
    from mcm_solarcheck.services.payment import PaymentAmount

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-policy-mismatch")
    assert persistence.introductory_offers.reserve(
        "user-sepa-policy-mismatch", "payment-sepa-policy", policy_version=2, now=now
    )

    payment = services.sepa_checkout.checkout(
        "payment-sepa-policy",
        user_id="user-sepa-policy-mismatch",
        project_id="project-user-sepa-policy-mismatch",
        job_id="job-user-sepa-policy-mismatch",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-policy-mismatch",
        now=now,
    )

    assert payment.amount == PaymentAmount(14500, "EUR")
    assert persistence.introductory_offers.is_reserved(
        "user-sepa-policy-mismatch", "payment-sepa-policy", policy_version=2
    )


def test_sepa_used_offer_is_not_reissued_for_new_payment(tmp_path) -> None:
    from mcm_solarcheck.services.payment import PaymentAmount

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-used")
    persistence.introductory_offers.mark_used(
        "user-sepa-used", "payment-sepa-used-original", policy_version=1, used_at=now
    )

    payment = services.sepa_checkout.checkout(
        "payment-sepa-used-next",
        user_id="user-sepa-used",
        project_id="project-user-sepa-used",
        job_id="job-user-sepa-used",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-used",
        now=now,
    )

    assert payment.amount == PaymentAmount(14500, "EUR")
    assert persistence.introductory_offers.has_used("user-sepa-used")


def test_sepa_released_offer_can_be_reserved_by_new_payment(tmp_path) -> None:
    from mcm_solarcheck.services.payment import PaymentAmount

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-released")
    assert persistence.introductory_offers.reserve(
        "user-sepa-released", "payment-sepa-released-old", policy_version=1, now=now
    )
    persistence.introductory_offers.release(
        "user-sepa-released", "payment-sepa-released-old"
    )

    payment = services.sepa_checkout.checkout(
        "payment-sepa-released-new",
        user_id="user-sepa-released",
        project_id="project-user-sepa-released",
        job_id="job-user-sepa-released",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-released",
        now=now,
    )

    assert payment.amount == PaymentAmount(5900, "EUR")
    assert persistence.introductory_offers.is_reserved(
        "user-sepa-released", "payment-sepa-released-new", policy_version=1
    )


def test_failed_sepa_pricing_releases_new_introductory_reservation(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-pricing-fail")

    def fail_create_payment(*args, **kwargs):
        raise RuntimeError("SEPA pricing failed")

    services.sepa_checkout._pricing.create_payment = fail_create_payment

    with pytest.raises(RuntimeError, match="SEPA pricing failed"):
        services.sepa_checkout.checkout(
            "payment-sepa-pricing-fail",
            user_id="user-sepa-pricing-fail",
            project_id="project-user-sepa-pricing-fail",
            job_id="job-user-sepa-pricing-fail",
            plant_kwp=750,
            provider_id="provider-a",
            merchant_account_id="merchant-user-sepa-pricing-fail",
            now=now,
        )

    assert persistence.introductory_offers.reserve(
        "user-sepa-pricing-fail",
        "payment-sepa-pricing-retry",
        policy_version=1,
        now=now,
    )


def test_sepa_checkout_retry_preserves_existing_payment_amount(tmp_path) -> None:
    from mcm_solarcheck.services.payment import PaymentAmount

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-existing-payment")
    first = services.sepa_checkout.checkout(
        "payment-sepa-existing",
        user_id="user-sepa-existing-payment",
        project_id="project-user-sepa-existing-payment",
        job_id="job-user-sepa-existing-payment",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-existing-payment",
        now=now,
    )

    second = services.sepa_checkout.checkout(
        "payment-sepa-existing",
        user_id="user-sepa-existing-payment",
        project_id="project-user-sepa-existing-payment",
        job_id="job-user-sepa-existing-payment",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-existing-payment",
        now=now,
    )

    assert first.amount == PaymentAmount(5900, "EUR")
    assert second.amount == first.amount


def test_sepa_checkout_retry_rejects_changed_user_identity(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-owner")
    services.sepa_checkout.checkout(
        "payment-sepa-owner",
        user_id="user-sepa-owner",
        project_id="project-user-sepa-owner",
        job_id="job-user-sepa-owner",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-owner",
        now=now,
    )

    with pytest.raises(PermissionError):
        services.sepa_checkout.checkout(
            "payment-sepa-owner",
            user_id="other-user",
            project_id="project-user-sepa-owner",
            job_id="job-user-sepa-owner",
            plant_kwp=750,
            provider_id="provider-a",
            merchant_account_id="merchant-user-sepa-owner",
            now=now,
        )


def test_sepa_checkout_retry_rejects_changed_project_identity(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-project")
    services.sepa_checkout.checkout(
        "payment-sepa-project",
        user_id="user-sepa-project",
        project_id="project-user-sepa-project",
        job_id="job-user-sepa-project",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-project",
        now=now,
    )

    with pytest.raises(PermissionError):
        services.sepa_checkout.checkout(
            "payment-sepa-project",
            user_id="user-sepa-project",
            project_id="other-project",
            job_id="job-user-sepa-project",
            plant_kwp=750,
            provider_id="provider-a",
            merchant_account_id="merchant-user-sepa-project",
            now=now,
        )


def test_sepa_checkout_retry_rejects_changed_plant_size(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-plant")
    services.sepa_checkout.checkout(
        "payment-sepa-plant",
        user_id="user-sepa-plant",
        project_id="project-user-sepa-plant",
        job_id="job-user-sepa-plant",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-plant",
        now=now,
    )

    with pytest.raises(ValueError, match="plant"):
        services.sepa_checkout.checkout(
            "payment-sepa-plant",
            user_id="user-sepa-plant",
            project_id="project-user-sepa-plant",
            job_id="job-user-sepa-plant",
            plant_kwp=751,
            provider_id="provider-a",
            merchant_account_id="merchant-user-sepa-plant",
            now=now,
        )


def test_sepa_checkout_retry_rejects_changed_merchant_account(tmp_path) -> None:
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-merchant-retry")
    services.sepa_checkout.checkout(
        "payment-sepa-merchant-retry",
        user_id="user-sepa-merchant-retry",
        project_id="project-user-sepa-merchant-retry",
        job_id="job-user-sepa-merchant-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-merchant-retry",
        now=now,
    )
    persistence.merchant_accounts.save(
        MerchantAccount("merchant-sepa-other", "provider-a", MerchantAccountKind.BANK, "SEPA")
    )

    with pytest.raises(ValueError, match="merchant"):
        services.sepa_checkout.checkout(
            "payment-sepa-merchant-retry",
            user_id="user-sepa-merchant-retry",
            project_id="project-user-sepa-merchant-retry",
            job_id="job-user-sepa-merchant-retry",
            plant_kwp=750,
            provider_id="provider-a",
            merchant_account_id="merchant-sepa-other",
            now=now,
        )


def test_sepa_checkout_retry_preserves_processing_snapshot(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-snapshot")
    first = services.sepa_checkout.checkout(
        "payment-sepa-snapshot",
        user_id="user-sepa-snapshot",
        project_id="project-user-sepa-snapshot",
        job_id="job-user-sepa-snapshot",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-snapshot",
        now=now,
    )

    second = services.sepa_checkout.checkout(
        "payment-sepa-snapshot",
        user_id="user-sepa-snapshot",
        project_id="project-user-sepa-snapshot",
        job_id="job-user-sepa-snapshot",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-snapshot",
        now=now,
    )

    assert second.method == first.method
    assert second.merchant_account_id == first.merchant_account_id
    assert second.merchant_account_version == first.merchant_account_version
    assert second.provider_id == first.provider_id


def test_sepa_checkout_retry_preserves_tariff_snapshot(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-tariff-snapshot")
    first = services.sepa_checkout.checkout(
        "payment-sepa-tariff-snapshot",
        user_id="user-sepa-tariff-snapshot",
        project_id="project-user-sepa-tariff-snapshot",
        job_id="job-user-sepa-tariff-snapshot",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-tariff-snapshot",
        now=now,
    )

    second = services.sepa_checkout.checkout(
        "payment-sepa-tariff-snapshot",
        user_id="user-sepa-tariff-snapshot",
        project_id="project-user-sepa-tariff-snapshot",
        job_id="job-user-sepa-tariff-snapshot",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-tariff-snapshot",
        now=now,
    )

    assert second.tariff_version == first.tariff_version
    assert second.plant_kwp == first.plant_kwp


def test_sepa_checkout_retry_keeps_payment_after_intro_reservation_release(tmp_path) -> None:
    from mcm_solarcheck.services.payment import PaymentAmount

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-release-retry")
    first = services.sepa_checkout.checkout(
        "payment-sepa-release-retry",
        user_id="user-sepa-release-retry",
        project_id="project-user-sepa-release-retry",
        job_id="job-user-sepa-release-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-release-retry",
        now=now,
    )
    persistence.introductory_offers.release(
        "user-sepa-release-retry", "payment-sepa-release-retry"
    )

    second = services.sepa_checkout.checkout(
        "payment-sepa-release-retry",
        user_id="user-sepa-release-retry",
        project_id="project-user-sepa-release-retry",
        job_id="job-user-sepa-release-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-release-retry",
        now=now,
    )

    assert first.amount == PaymentAmount(5900, "EUR")
    assert second.amount == first.amount


def test_sepa_checkout_retry_preserves_payment_after_intro_deadline(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.payment import PaymentAmount

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-existing-deadline")
    first = services.sepa_checkout.checkout(
        "payment-sepa-existing-deadline",
        user_id="user-sepa-existing-deadline",
        project_id="project-user-sepa-existing-deadline",
        job_id="job-user-sepa-existing-deadline",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-existing-deadline",
        now=now,
    )

    second = services.sepa_checkout.checkout(
        "payment-sepa-existing-deadline",
        user_id="user-sepa-existing-deadline",
        project_id="project-user-sepa-existing-deadline",
        job_id="job-user-sepa-existing-deadline",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-existing-deadline",
        now=datetime(2027, 1, 1, tzinfo=timezone.utc),
    )

    assert first.amount == PaymentAmount(5900, "EUR")
    assert second.amount == first.amount


def test_sepa_checkout_retry_returns_persisted_payment_identity(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-persisted")
    first = services.sepa_checkout.checkout(
        "payment-sepa-persisted",
        user_id="user-sepa-persisted",
        project_id="project-user-sepa-persisted",
        job_id="job-user-sepa-persisted",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-persisted",
        now=now,
    )

    second = services.sepa_checkout.checkout(
        "payment-sepa-persisted",
        user_id="user-sepa-persisted",
        project_id="project-user-sepa-persisted",
        job_id="job-user-sepa-persisted",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-persisted",
        now=now,
    )

    assert second.payment_id == first.payment_id
    assert second.user_id == first.user_id
    assert second.project_id == first.project_id
    assert second.job_id == first.job_id
    assert second.status == first.status


def test_sepa_voucher_discounts_introductory_price(tmp_path) -> None:
    from datetime import timedelta
    from mcm_solarcheck.services.payment import PaymentAmount
    from mcm_solarcheck.services.voucher import FlightPlanVoucher

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-voucher")
    persistence.vouchers.create(
        FlightPlanVoucher("SEPA-VOUCHER", now - timedelta(days=1), now + timedelta(days=1))
    )

    payment = services.sepa_checkout.checkout(
        "payment-sepa-voucher",
        user_id="user-sepa-voucher",
        project_id="project-user-sepa-voucher",
        job_id="job-user-sepa-voucher",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-voucher",
        voucher_code="SEPA-VOUCHER",
        now=now,
    )

    assert payment.amount == PaymentAmount(5310, "EUR")
    assert persistence.vouchers.get("SEPA-VOUCHER").redeemed_payment_id == payment.payment_id


def test_sepa_voucher_retry_keeps_discounted_amount(tmp_path) -> None:
    from datetime import timedelta
    from mcm_solarcheck.services.payment import PaymentAmount
    from mcm_solarcheck.services.voucher import FlightPlanVoucher

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-voucher-retry")
    persistence.vouchers.create(
        FlightPlanVoucher("SEPA-VOUCHER-RETRY", now - timedelta(days=1), now + timedelta(days=1))
    )
    first = services.sepa_checkout.checkout(
        "payment-sepa-voucher-retry",
        user_id="user-sepa-voucher-retry",
        project_id="project-user-sepa-voucher-retry",
        job_id="job-user-sepa-voucher-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-voucher-retry",
        voucher_code="SEPA-VOUCHER-RETRY",
        now=now,
    )

    second = services.sepa_checkout.checkout(
        "payment-sepa-voucher-retry",
        user_id="user-sepa-voucher-retry",
        project_id="project-user-sepa-voucher-retry",
        job_id="job-user-sepa-voucher-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-voucher-retry",
        voucher_code="SEPA-VOUCHER-RETRY",
        now=now,
    )

    assert first.amount == PaymentAmount(5310, "EUR")
    assert second.amount == first.amount


def test_sepa_voucher_retry_does_not_change_redemption_evidence(tmp_path) -> None:
    from datetime import timedelta
    from mcm_solarcheck.services.voucher import FlightPlanVoucher

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-voucher-evidence")
    persistence.vouchers.create(
        FlightPlanVoucher("SEPA-VOUCHER-EVIDENCE", now - timedelta(days=1), now + timedelta(days=1))
    )
    services.sepa_checkout.checkout(
        "payment-sepa-voucher-evidence",
        user_id="user-sepa-voucher-evidence",
        project_id="project-user-sepa-voucher-evidence",
        job_id="job-user-sepa-voucher-evidence",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-voucher-evidence",
        voucher_code="SEPA-VOUCHER-EVIDENCE",
        now=now,
    )
    before = persistence.vouchers.get("SEPA-VOUCHER-EVIDENCE")

    services.sepa_checkout.checkout(
        "payment-sepa-voucher-evidence",
        user_id="user-sepa-voucher-evidence",
        project_id="project-user-sepa-voucher-evidence",
        job_id="job-user-sepa-voucher-evidence",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-voucher-evidence",
        voucher_code="SEPA-VOUCHER-EVIDENCE",
        now=now + timedelta(minutes=1),
    )
    after = persistence.vouchers.get("SEPA-VOUCHER-EVIDENCE")

    assert after == before


def test_sepa_retry_cannot_reprice_existing_payment_with_new_voucher(tmp_path) -> None:
    from datetime import timedelta
    from mcm_solarcheck.services.payment import PaymentAmount
    from mcm_solarcheck.services.voucher import FlightPlanVoucher

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-late-voucher")
    first = services.sepa_checkout.checkout(
        "payment-sepa-late-voucher",
        user_id="user-sepa-late-voucher",
        project_id="project-user-sepa-late-voucher",
        job_id="job-user-sepa-late-voucher",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-late-voucher",
        now=now,
    )
    persistence.vouchers.create(
        FlightPlanVoucher("SEPA-LATE-VOUCHER", now - timedelta(days=1), now + timedelta(days=1))
    )

    second = services.sepa_checkout.checkout(
        "payment-sepa-late-voucher",
        user_id="user-sepa-late-voucher",
        project_id="project-user-sepa-late-voucher",
        job_id="job-user-sepa-late-voucher",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-late-voucher",
        voucher_code="SEPA-LATE-VOUCHER",
        now=now,
    )

    assert first.amount == PaymentAmount(5900, "EUR")
    assert second.amount == first.amount
    assert persistence.vouchers.get("SEPA-LATE-VOUCHER").redeemed is False


def test_sepa_voucher_retry_cannot_switch_to_different_voucher(tmp_path) -> None:
    from datetime import timedelta
    from mcm_solarcheck.services.voucher import FlightPlanVoucher

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-switch-voucher")
    for code in ("SEPA-VOUCHER-FIRST", "SEPA-VOUCHER-SECOND"):
        persistence.vouchers.create(
            FlightPlanVoucher(code, now - timedelta(days=1), now + timedelta(days=1))
        )
    first = services.sepa_checkout.checkout(
        "payment-sepa-switch-voucher",
        user_id="user-sepa-switch-voucher",
        project_id="project-user-sepa-switch-voucher",
        job_id="job-user-sepa-switch-voucher",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-switch-voucher",
        voucher_code="SEPA-VOUCHER-FIRST",
        now=now,
    )

    second = services.sepa_checkout.checkout(
        "payment-sepa-switch-voucher",
        user_id="user-sepa-switch-voucher",
        project_id="project-user-sepa-switch-voucher",
        job_id="job-user-sepa-switch-voucher",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-switch-voucher",
        voucher_code="SEPA-VOUCHER-SECOND",
        now=now,
    )

    assert second.amount == first.amount
    assert persistence.vouchers.get("SEPA-VOUCHER-FIRST").redeemed_payment_id == first.payment_id
    assert persistence.vouchers.get("SEPA-VOUCHER-SECOND").redeemed is False


def test_sepa_checkout_retry_rejects_changed_provider(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-provider-retry")
    services.sepa_checkout.checkout(
        "payment-sepa-provider-retry",
        user_id="user-sepa-provider-retry",
        project_id="project-user-sepa-provider-retry",
        job_id="job-user-sepa-provider-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-provider-retry",
        now=now,
    )
    services.sepa_checkout._providers = PaymentProviderRegistry((
        PaymentProviderCapabilities("provider-a", frozenset({PaymentMethod.SEPA_DIRECT_DEBIT})),
        PaymentProviderCapabilities("provider-b", frozenset({PaymentMethod.SEPA_DIRECT_DEBIT})),
    ))

    with pytest.raises(ValueError, match="provider"):
        services.sepa_checkout.checkout(
            "payment-sepa-provider-retry",
            user_id="user-sepa-provider-retry",
            project_id="project-user-sepa-provider-retry",
            job_id="job-user-sepa-provider-retry",
            plant_kwp=750,
            provider_id="provider-b",
            merchant_account_id="merchant-user-sepa-provider-retry",
            now=now,
        )


def test_sepa_checkout_retry_requires_sepa_payment_snapshot(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-method-retry")
    payment = services.sepa_checkout.checkout(
        "payment-sepa-method-retry",
        user_id="user-sepa-method-retry",
        project_id="project-user-sepa-method-retry",
        job_id="job-user-sepa-method-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-method-retry",
        now=now,
    )
    assert payment.method is PaymentMethod.SEPA_DIRECT_DEBIT

    retried = services.sepa_checkout.checkout(
        "payment-sepa-method-retry",
        user_id="user-sepa-method-retry",
        project_id="project-user-sepa-method-retry",
        job_id="job-user-sepa-method-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-method-retry",
        now=now,
    )

    assert retried.method is PaymentMethod.SEPA_DIRECT_DEBIT


def test_sepa_checkout_retry_preserves_authorized_payment(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-authorized-retry")
    services.sepa_checkout.checkout(
        "payment-sepa-authorized-retry",
        user_id="user-sepa-authorized-retry",
        project_id="project-user-sepa-authorized-retry",
        job_id="job-user-sepa-authorized-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-authorized-retry",
        now=now,
    )
    authorized = persistence.payments.authorize(
        "payment-sepa-authorized-retry", "user-sepa-authorized-retry",
        "project-user-sepa-authorized-retry", "provider-reference"
    )

    retried = services.sepa_checkout.checkout(
        "payment-sepa-authorized-retry",
        user_id="user-sepa-authorized-retry",
        project_id="project-user-sepa-authorized-retry",
        job_id="job-user-sepa-authorized-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-authorized-retry",
        now=now,
    )

    assert retried == authorized


def test_sepa_checkout_retry_preserves_captured_payment(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-captured-retry")
    services.sepa_checkout.checkout(
        "payment-sepa-captured-retry",
        user_id="user-sepa-captured-retry",
        project_id="project-user-sepa-captured-retry",
        job_id="job-user-sepa-captured-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-captured-retry",
        now=now,
    )
    persistence.payments.authorize(
        "payment-sepa-captured-retry", "user-sepa-captured-retry",
        "project-user-sepa-captured-retry", "provider-reference"
    )
    captured = persistence.payments.capture(
        "payment-sepa-captured-retry", "user-sepa-captured-retry",
        "project-user-sepa-captured-retry"
    )

    retried = services.sepa_checkout.checkout(
        "payment-sepa-captured-retry",
        user_id="user-sepa-captured-retry",
        project_id="project-user-sepa-captured-retry",
        job_id="job-user-sepa-captured-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-captured-retry",
        now=now,
    )

    assert retried == captured


def test_sepa_checkout_retry_preserves_voided_payment(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-voided-retry")
    services.sepa_checkout.checkout(
        "payment-sepa-voided-retry",
        user_id="user-sepa-voided-retry",
        project_id="project-user-sepa-voided-retry",
        job_id="job-user-sepa-voided-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-voided-retry",
        now=now,
    )
    persistence.payments.authorize(
        "payment-sepa-voided-retry", "user-sepa-voided-retry",
        "project-user-sepa-voided-retry", "provider-reference"
    )
    voided = persistence.payments.void(
        "payment-sepa-voided-retry", "user-sepa-voided-retry",
        "project-user-sepa-voided-retry"
    )

    retried = services.sepa_checkout.checkout(
        "payment-sepa-voided-retry",
        user_id="user-sepa-voided-retry",
        project_id="project-user-sepa-voided-retry",
        job_id="job-user-sepa-voided-retry",
        plant_kwp=750,
        provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-voided-retry",
        now=now,
    )

    assert retried == voided


def test_sepa_checkout_retry_does_not_call_pricing(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-no-reprice")
    first = services.sepa_checkout.checkout(
        "payment-sepa-no-reprice", user_id="user-sepa-no-reprice",
        project_id="project-user-sepa-no-reprice", job_id="job-user-sepa-no-reprice",
        plant_kwp=750, provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-no-reprice", now=now,
    )

    def fail_pricing(*args, **kwargs):
        raise AssertionError("retry must not call pricing")

    services.sepa_checkout._pricing.create_payment = fail_pricing
    retried = services.sepa_checkout.checkout(
        "payment-sepa-no-reprice", user_id="user-sepa-no-reprice",
        project_id="project-user-sepa-no-reprice", job_id="job-user-sepa-no-reprice",
        plant_kwp=750, provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-no-reprice", now=now,
    )

    assert retried == first


def test_sepa_checkout_retry_does_not_read_current_tariff(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-no-retariff")
    first = services.sepa_checkout.checkout(
        "payment-sepa-no-retariff", user_id="user-sepa-no-retariff",
        project_id="project-user-sepa-no-retariff", job_id="job-user-sepa-no-retariff",
        plant_kwp=750, provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-no-retariff", now=now,
    )

    def fail_tariff(*args, **kwargs):
        raise AssertionError("retry must not read tariff")

    services.sepa_checkout._tariffs.current = fail_tariff
    retried = services.sepa_checkout.checkout(
        "payment-sepa-no-retariff", user_id="user-sepa-no-retariff",
        project_id="project-user-sepa-no-retariff", job_id="job-user-sepa-no-retariff",
        plant_kwp=750, provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-no-retariff", now=now,
    )

    assert retried == first


def test_sepa_checkout_retry_uses_explicit_payment_store(tmp_path) -> None:
    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-explicit-store")
    first = services.sepa_checkout.checkout(
        "payment-sepa-explicit-store", user_id="user-sepa-explicit-store",
        project_id="project-user-sepa-explicit-store", job_id="job-user-sepa-explicit-store",
        plant_kwp=750, provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-explicit-store", now=now,
    )

    services.sepa_checkout._pricing._payments = object()
    retried = services.sepa_checkout.checkout(
        "payment-sepa-explicit-store", user_id="user-sepa-explicit-store",
        project_id="project-user-sepa-explicit-store", job_id="job-user-sepa-explicit-store",
        plant_kwp=750, provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-explicit-store", now=now,
    )

    assert retried == first


def test_sepa_checkout_retry_does_not_touch_voucher_store(tmp_path) -> None:
    from datetime import timedelta
    from mcm_solarcheck.services.voucher import FlightPlanVoucher

    persistence, services, now = _verified_sepa_intro_services(tmp_path, "user-sepa-no-revoucher")
    persistence.vouchers.create(
        FlightPlanVoucher("SEPA-NO-REVOUCHER", now - timedelta(days=1), now + timedelta(days=1))
    )
    first = services.sepa_checkout.checkout(
        "payment-sepa-no-revoucher", user_id="user-sepa-no-revoucher",
        project_id="project-user-sepa-no-revoucher", job_id="job-user-sepa-no-revoucher",
        plant_kwp=750, provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-no-revoucher",
        voucher_code="SEPA-NO-REVOUCHER", now=now,
    )
    before = persistence.vouchers.get("SEPA-NO-REVOUCHER")

    services.sepa_checkout._pricing._vouchers = object()
    retried = services.sepa_checkout.checkout(
        "payment-sepa-no-revoucher", user_id="user-sepa-no-revoucher",
        project_id="project-user-sepa-no-revoucher", job_id="job-user-sepa-no-revoucher",
        plant_kwp=750, provider_id="provider-a",
        merchant_account_id="merchant-user-sepa-no-revoucher",
        voucher_code="SEPA-NO-REVOUCHER", now=now,
    )

    assert retried == first
    assert persistence.vouchers.get("SEPA-NO-REVOUCHER") == before


def test_payment_closeout_card_capture_reaches_execution_evidence(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.payment import PaymentStatus
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    persistence.merchant_accounts.save(MerchantAccount("merchant-close-card", "provider-a", MerchantAccountKind.CARD_PROCESSOR, "card"))
    persistence.tariffs.save(initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc)))
    from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus
    persistence.compute_jobs.create(ComputeJob("job-close-card", "user-close", "project-close", ComputeJobStatus.COMPLETED))
    persistence.billing.create(ComputeJobBilling(ComputeJobDelivery("job-close-card", "user-close", "project-close")))
    services = online_services(persistence)
    payment = services.payment_checkout.checkout(
        "payment-close-card", user_id="user-close", project_id="project-close",
        job_id="job-close-card", plant_kwp=750, method=PaymentMethod.CARD,
        provider_id="provider-a", merchant_account_id="merchant-close-card",
        now=datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc),
    )
    services.billing.mark_export_completed("job-close-card", user_id="user-close", project_id="project-close")
    services.billing.mark_report_retrieved("job-close-card", user_id="user-close", project_id="project-close")
    services.billing.release("job-close-card", user_id="user-close", project_id="project-close")
    captured = services.payment_capture.capture("payment-close-card", user_id="user-close", project_id="project-close")

    assert payment.status is PaymentStatus.AUTHORIZED
    assert captured.status is PaymentStatus.CAPTURED
    services.payment_execution.require_succeeded(captured)


def test_payment_closeout_card_fails_execution_evidence_before_capture(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    persistence.merchant_accounts.save(MerchantAccount("merchant-close-uncaptured", "provider-a", MerchantAccountKind.CARD_PROCESSOR, "card"))
    persistence.tariffs.save(initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc)))
    persistence.billing.create(ComputeJobBilling(ComputeJobDelivery("job-close-uncaptured", "user-close", "project-close")))
    services = online_services(persistence)
    authorized = services.payment_checkout.checkout(
        "payment-close-uncaptured", user_id="user-close", project_id="project-close",
        job_id="job-close-uncaptured", plant_kwp=750, method=PaymentMethod.CARD,
        provider_id="provider-a", merchant_account_id="merchant-close-uncaptured",
        now=datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="captured payment"):
        services.payment_execution.require_succeeded(authorized)


def test_payment_closeout_sepa_submission_reaches_execution_evidence(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.sepa import SepaMandate
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    persistence.merchant_accounts.save(MerchantAccount("merchant-close-sepa", "provider-a", MerchantAccountKind.BANK, "bank"))
    persistence.tariffs.save(initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc)))
    from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus
    persistence.compute_jobs.create(ComputeJob("job-close-sepa", "user-close-sepa", "project-close-sepa", ComputeJobStatus.COMPLETED))
    persistence.billing.create(ComputeJobBilling(ComputeJobDelivery("job-close-sepa", "user-close-sepa", "project-close-sepa")))
    persistence.sepa_mandates.create(SepaMandate("mandate-close-sepa", "user-close-sepa", "provider-a"))
    persistence.sepa_mandates.activate("mandate-close-sepa", "user-close-sepa", "provider-mandate-close")
    services = online_services(persistence)
    payment = services.sepa_checkout.checkout(
        "payment-close-sepa", user_id="user-close-sepa", project_id="project-close-sepa",
        job_id="job-close-sepa", plant_kwp=750, provider_id="provider-a",
        merchant_account_id="merchant-close-sepa", now=datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc),
    )
    services.billing.mark_export_completed("job-close-sepa", user_id="user-close-sepa", project_id="project-close-sepa")
    services.billing.mark_report_retrieved("job-close-sepa", user_id="user-close-sepa", project_id="project-close-sepa")
    services.billing.release("job-close-sepa", user_id="user-close-sepa", project_id="project-close-sepa")
    services.sepa_payment.submit("payment-close-sepa", "mandate-close-sepa", user_id="user-close-sepa", project_id="project-close-sepa")

    services.payment_execution.require_succeeded(persistence.payments.get(payment.payment_id))


def test_payment_closeout_sepa_fails_execution_evidence_before_submission(tmp_path) -> None:
    from datetime import datetime, timezone
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff

    persistence = setup_persistence(tmp_path, secret_configured=True)
    persistence.merchant_accounts.save(MerchantAccount("merchant-close-sepa-missing", "provider-a", MerchantAccountKind.BANK, "bank"))
    persistence.tariffs.save(initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc)))
    persistence.billing.create(ComputeJobBilling(ComputeJobDelivery("job-close-sepa-missing", "user-close-sepa", "project-close-sepa")))
    services = online_services(persistence)
    payment = services.sepa_checkout.checkout(
        "payment-close-sepa-missing", user_id="user-close-sepa", project_id="project-close-sepa",
        job_id="job-close-sepa-missing", plant_kwp=750, provider_id="provider-a",
        merchant_account_id="merchant-close-sepa-missing", now=datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="submitted SEPA payment"):
        services.payment_execution.require_succeeded(payment)


def test_payment_closeout_voucher_amount_survives_capture_and_execution_evidence(tmp_path) -> None:
    from datetime import datetime, timedelta, timezone
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
    from mcm_solarcheck.services.payment import PaymentAmount
    from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff
    from mcm_solarcheck.services.voucher import FlightPlanVoucher

    persistence = setup_persistence(tmp_path, secret_configured=True)
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    persistence.merchant_accounts.save(MerchantAccount("merchant-close-voucher", "provider-a", MerchantAccountKind.CARD_PROCESSOR, "card"))
    persistence.tariffs.save(initial_solarcheck_tariff(datetime(2026, 9, 30, tzinfo=timezone.utc)))
    persistence.vouchers.create(FlightPlanVoucher("CLOSE-VOUCHER", now - timedelta(days=1), now + timedelta(days=1)))
    from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus
    persistence.compute_jobs.create(ComputeJob("job-close-voucher", "user-close-voucher", "project-close-voucher", ComputeJobStatus.COMPLETED))
    persistence.billing.create(ComputeJobBilling(ComputeJobDelivery("job-close-voucher", "user-close-voucher", "project-close-voucher")))
    services = online_services(persistence)
    authorized = services.payment_checkout.checkout(
        "payment-close-voucher", user_id="user-close-voucher", project_id="project-close-voucher",
        job_id="job-close-voucher", plant_kwp=750, method=PaymentMethod.CARD,
        provider_id="provider-a", merchant_account_id="merchant-close-voucher",
        voucher_code="CLOSE-VOUCHER", now=now,
    )
    services.billing.mark_export_completed("job-close-voucher", user_id="user-close-voucher", project_id="project-close-voucher")
    services.billing.mark_report_retrieved("job-close-voucher", user_id="user-close-voucher", project_id="project-close-voucher")
    services.billing.release("job-close-voucher", user_id="user-close-voucher", project_id="project-close-voucher")
    captured = services.payment_capture.capture("payment-close-voucher", user_id="user-close-voucher", project_id="project-close-voucher")

    assert authorized.amount == PaymentAmount(13050, "EUR")
    assert captured.amount == authorized.amount
    assert persistence.vouchers.get("CLOSE-VOUCHER").redeemed_payment_id == captured.payment_id
    services.payment_execution.require_succeeded(captured)



def test_online_report_retrieval_requires_paid_order(tmp_path) -> None:
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)
    persistence.billing.create(ComputeJobBilling(ComputeJobDelivery("job-report-unpaid", "user-report-unpaid", "project-report-unpaid", export_completed=True)))
    persistence.reports.path_for("job-report-unpaid").write_bytes(b"unpaid-report")

    with pytest.raises(ValueError, match="paid order"):
        services.report_delivery.retrieve("job-report-unpaid", user_id="user-report-unpaid", project_id="project-report-unpaid")


def test_online_report_retrieval_rejects_payment_identity_mismatch(tmp_path) -> None:
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount

    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)
    persistence.billing.create(ComputeJobBilling(ComputeJobDelivery("job-report-mismatch", "user-report", "project-report", export_completed=True)))
    persistence.payments.create(OnlinePayment("payment-report-mismatch", "other-user", "other-project", "job-report-mismatch", PaymentAmount(9500, "EUR")))
    persistence.reports.path_for("job-report-mismatch").write_bytes(b"mismatched-report")

    with pytest.raises(PermissionError, match="payment ownership"):
        services.report_delivery.retrieve("job-report-mismatch", user_id="user-report", project_id="project-report")


def test_online_report_retrieval_accepts_matching_paid_order(tmp_path) -> None:
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount

    persistence = setup_persistence(tmp_path, secret_configured=True)
    services = online_services(persistence)
    persistence.billing.create(ComputeJobBilling(ComputeJobDelivery("job-report-paid", "user-report-paid", "project-report-paid", export_completed=True)))
    persistence.payments.create(OnlinePayment("payment-report-paid", "user-report-paid", "project-report-paid", "job-report-paid", PaymentAmount(9500, "EUR")))
    persistence.reports.path_for("job-report-paid").write_bytes(b"paid-report")

    report = services.report_delivery.retrieve("job-report-paid", user_id="user-report-paid", project_id="project-report-paid")

    assert report.content == b"paid-report"


def test_online_report_retrieval_requires_completed_compute_job(tmp_path) -> None:
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount

    persistence = setup_persistence(tmp_path, secret_configured=True)
    persistence.billing.create(ComputeJobBilling(ComputeJobDelivery("job-report-no-compute", "user-report-no-compute", "project-report-no-compute", export_completed=True)))
    persistence.payments.create(OnlinePayment("payment-report-no-compute", "user-report-no-compute", "project-report-no-compute", "job-report-no-compute", PaymentAmount(9500, "EUR")))
    services = online_services(persistence)
    with pytest.raises(ValueError, match="completed compute job"):
        services.report_delivery.retrieve("job-report-no-compute", user_id="user-report-no-compute", project_id="project-report-no-compute")


def test_online_report_retrieval_rejects_failed_compute_job(tmp_path) -> None:
    from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
    from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus
    from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
    persistence = setup_persistence(tmp_path, secret_configured=True)
    persistence.compute_jobs.create(ComputeJob("job-report-failed", "user-report-failed", "project-report-failed", ComputeJobStatus.FAILED))
    persistence.billing.create(ComputeJobBilling(ComputeJobDelivery("job-report-failed", "user-report-failed", "project-report-failed", export_completed=True)))
    persistence.payments.create(OnlinePayment("payment-report-failed", "user-report-failed", "project-report-failed", "job-report-failed", PaymentAmount(9500, "EUR")))
    services = online_services(persistence)
    with pytest.raises(ValueError, match="completed compute job"):
        services.report_delivery.retrieve("job-report-failed", user_id="user-report-failed", project_id="project-report-failed")
