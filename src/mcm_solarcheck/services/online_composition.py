"""Provider-neutral service composition for SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from mcm_solarcheck.infrastructure.online_persistence import OnlinePersistence
from mcm_solarcheck.domain.pricing import PricingRule
from mcm_solarcheck.infrastructure.smtp_email import SMTPEmailSender
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.compute_jobs import ComputeJobLease, ComputeJobService
from mcm_solarcheck.services.email import RegistrationEmailConfig, ReportRecoveryEmailConfig
from mcm_solarcheck.services.invoice import InvoiceBasisService
from mcm_solarcheck.services.invoice_admin_delivery import InvoiceAdminDeliveryService
from mcm_solarcheck.services.invoice_creation import InvoiceCreationService, InvoiceRenderConfig
from mcm_solarcheck.services.merchant_binding import MerchantAccountBindingService
from mcm_solarcheck.services.online_activation import OnlineProductionActivation
from mcm_solarcheck.services.online_authentication import OnlineAuthenticationService
from mcm_solarcheck.services.online_credentials import PasswordCredentialService
from mcm_solarcheck.services.online_login import OnlineLoginService
from mcm_solarcheck.services.online_admin import OnlineAdminActions
from mcm_solarcheck.services.online_registration import OnlineRegistrationService
from mcm_solarcheck.services.online_admin_readiness import (
    ConfigurationReadiness,
    OnlineAdminReadinessService,
)
from mcm_solarcheck.services.payment_capture import PaymentCaptureService
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.services.project_creation import ProjectCreationService
from mcm_solarcheck.services.project_pricing import DiscountEligibility, ProjectPricingService
from mcm_solarcheck.services.project_upload import ProjectUploadService
from mcm_solarcheck.services.project_processing import ProjectProcessingService, ComputeJobProcessingStateRecorder
from mcm_solarcheck.importers.project import import_m3t_project
from mcm_solarcheck.storage.import_store import store_project_import
from mcm_solarcheck.services.payment_checkout import OnlinePaymentCheckoutService
from mcm_solarcheck.services.payment_execution import PaymentExecutionEvidence
from mcm_solarcheck.services.payment_gateway import PaymentAuthorizationService, PaymentGateway
from mcm_solarcheck.services.payment_pricing import PaymentPricingService
from mcm_solarcheck.services.payment_provider import PaymentProviderRegistry
from mcm_solarcheck.services.payment_void import PaymentVoidService
from mcm_solarcheck.services.released_invoice import ReleasedInvoiceService
from mcm_solarcheck.services.report_delivery import ReportDeliveryService
from mcm_solarcheck.services.report_recovery import ReportRecoveryService
from mcm_solarcheck.services.report_recovery_notification import ReportRecoveryNotificationService
from mcm_solarcheck.services.sepa_checkout import OnlineSepaCheckoutService
from mcm_solarcheck.services.sepa_payment import SepaPaymentGateway, SepaPaymentService
from mcm_solarcheck.services.sepa_reconciliation import SepaReconciliationService
from mcm_solarcheck.services.smtp_admin import (
    SMTPAdminActions,
    SMTPAdminAuthorization,
    SMTPAdminMutationGuard,
    SMTPAdminService,
)


class EntitledComputeJobService:
    """Online-only gate that requires durable product access before job creation."""

    def __init__(self, jobs: ComputeJobService, entitlements) -> None:
        self._jobs = jobs
        self._entitlements = entitlements

    def create(self, *, job_id: str, user_id: str, project_id: str):
        self._entitlements.require_active(user_id)
        return self._jobs.create(job_id=job_id, user_id=user_id, project_id=project_id)

    def __getattr__(self, name):
        return getattr(self._jobs, name)


class _OnlineReadinessBoundary:
    """Adapt composed admin readiness to the production activation contract."""

    def __init__(self, readiness: OnlineAdminReadinessService) -> None:
        self._readiness = readiness

    def require_production_ready(self) -> None:
        self._readiness.require_ready()


@dataclass(frozen=True)
class OnlineServices:
    projects: ProjectApplicationService
    project_creation: ProjectCreationService
    project_pricing: ProjectPricingService | None
    project_upload: ProjectUploadService
    project_processing: ProjectProcessingService
    registration: OnlineRegistrationService
    login: OnlineLoginService
    compute_jobs: EntitledComputeJobService
    billing: ComputeJobBillingService
    report_delivery: ReportDeliveryService
    report_recovery: ReportRecoveryService
    payment_checkout: OnlinePaymentCheckoutService
    payment_authorization: PaymentAuthorizationService
    payment_capture: PaymentCaptureService
    payment_void: PaymentVoidService
    sepa_checkout: OnlineSepaCheckoutService
    sepa_payment: SepaPaymentService
    sepa_reconciliation: SepaReconciliationService
    payment_execution: PaymentExecutionEvidence
    invoice_creation: InvoiceCreationService
    smtp_admin: SMTPAdminService
    admin_readiness: OnlineAdminReadinessService
    admin: OnlineAdminActions
    production: OnlineProductionActivation
    entitlements: object
    credentials: object
    sessions: object

    def require_production_ready(self) -> None:
        """Fail closed before enabling customer-facing commercial operation."""
        self.admin_readiness.require_ready()

    def activate_production(self) -> None:
        """Explicitly activate customer-facing operation after all readiness gates."""
        self.production.activate()

    def require_production_active(self) -> None:
        """Fail closed at customer-facing deployment entry boundaries."""
        self.production.require_active()


def build_online_services(
    persistence: OnlinePersistence,
    *,
    invoice_render: InvoiceRenderConfig,
    public_base_url: str,
    payment_gateway: PaymentGateway,
    sepa_gateway: SepaPaymentGateway,
    sepa_provider_id: str,
    payment_provider_readiness: ConfigurationReadiness,
    payment_providers: PaymentProviderRegistry,
    sepa_provider_readiness: ConfigurationReadiness,
    admin_authorization: SMTPAdminAuthorization,
    admin_mutation_guard: SMTPAdminMutationGuard,
    pricing_rule: PricingRule | None = None,
    discount_eligibility_for_project: Callable[[str, str], DiscountEligibility] | None = None,
    project_processing_lease: Callable[[], ComputeJobLease] | None = None,
) -> OnlineServices:
    """Compose services from durable stores and deployment-owned SMTP state."""
    if not isinstance(persistence, OnlinePersistence):
        raise TypeError("persistence must be OnlinePersistence")
    if not isinstance(invoice_render, InvoiceRenderConfig):
        raise TypeError("invoice_render must be InvoiceRenderConfig")

    smtp_admin = SMTPAdminService(persistence.smtp_settings, persistence.smtp_secrets)
    smtp_config = persistence.smtp_settings.get()
    smtp_password = persistence.smtp_secrets.resolve_for_delivery()
    sender = SMTPEmailSender(smtp_config, smtp_password)

    registration = OnlineRegistrationService(
        persistence.registrations,
        sender,
        RegistrationEmailConfig(
            sender=smtp_config.effective_sender_address,
            notify_to="solarcheck@mcm-dronetech.com",
            public_base_url=public_base_url,
        ),
        entitlements=persistence.entitlements,
    )

    login = OnlineLoginService(
        PasswordCredentialService(persistence.credentials),
        OnlineAuthenticationService(persistence.registrations),
    )

    compute_jobs_core = ComputeJobService(
        persistence.compute_jobs,
        load=persistence.compute_jobs,
        admission=persistence.compute_jobs,
        claims=persistence.compute_jobs,
    )
    compute_jobs = EntitledComputeJobService(compute_jobs_core, persistence.entitlements)
    billing = ComputeJobBillingService(persistence.billing, persistence.compute_jobs)
    report_delivery = ReportDeliveryService(persistence.billing, persistence.reports)
    report_notifications = ReportRecoveryNotificationService(
        sender,
        ReportRecoveryEmailConfig(
            sender=smtp_config.effective_sender_address,
            notify_to="solarcheck@mcm-dronetech.com",
        ),
    )
    report_recovery = ReportRecoveryService(
        report_notifications,
        persistence.report_recovery,
    )

    if payment_gateway is None:
        raise TypeError("payment_gateway is required for online services")
    for method in ("authorize", "capture", "void"):
        if not callable(getattr(payment_gateway, method, None)):
            raise TypeError(f"payment_gateway must provide {method}()")
    if sepa_gateway is None:
        raise TypeError("sepa_gateway is required for online services")
    if not callable(getattr(sepa_gateway, "submit", None)):
        raise TypeError("sepa_gateway must provide submit()")
    if not isinstance(sepa_provider_id, str) or not sepa_provider_id.strip():
        raise ValueError("sepa_provider_id must be non-empty")
    for readiness, name in (
        (payment_provider_readiness, "payment_provider_readiness"),
        (sepa_provider_readiness, "sepa_provider_readiness"),
    ):
        if not callable(getattr(readiness, "is_configured", None)):
            raise TypeError(f"{name} must provide is_configured()")

    admin_readiness = OnlineAdminReadinessService(
        smtp_admin,
        payment_provider_readiness,
        sepa_provider_readiness,
        persistence.tariffs,
        persistence.merchant_accounts,
    )
    production = OnlineProductionActivation(_OnlineReadinessBoundary(admin_readiness))
    admin = OnlineAdminActions(
        admin_readiness,
        SMTPAdminActions(
            smtp_admin,
            admin_authorization,
            admin_mutation_guard,
            persistence.smtp_admin_audit,
        ),
        payment_provider_readiness,
        sepa_provider_readiness,
    )

    payment_authorization = PaymentAuthorizationService(
        persistence.payments,
        payment_gateway,
        intents=persistence.payment_authorizations,
    )
    payment_pricing = PaymentPricingService(
        persistence.payments,
        persistence.vouchers,
        persistence.voucher_policy,
        persistence.priced_payments,
    )
    merchant_binding = MerchantAccountBindingService(persistence.merchant_accounts)
    payment_checkout = OnlinePaymentCheckoutService(
        payment_pricing,
        merchant_binding,
        payment_providers,
        payment_authorization,
        persistence.payments,
        persistence.tariffs,
        persistence.billing,
    )
    payment_capture = PaymentCaptureService(
        persistence.payments,
        persistence.billing,
        payment_gateway,
        persistence.payment_operations,
    )
    payment_void = PaymentVoidService(
        persistence.payments,
        payment_gateway,
        persistence.payment_operations,
    )
    sepa_checkout = OnlineSepaCheckoutService(
        payment_pricing,
        merchant_binding,
        payment_providers,
        persistence.payments,
        persistence.tariffs,
        persistence.billing,
    )
    sepa_payment = SepaPaymentService(
        persistence.payments,
        persistence.sepa_mandates,
        sepa_gateway,
        sepa_provider_id,
        collections=persistence.sepa_collections,
        submissions=persistence.sepa_submissions,
        billing=persistence.billing,
    )
    sepa_reconciliation = SepaReconciliationService(persistence.sepa_collections)
    payment_execution = PaymentExecutionEvidence(persistence.sepa_submissions)
    invoice_admin_delivery = InvoiceAdminDeliveryService(
        persistence.invoices,
        sender,
        sender_address=smtp_config.effective_sender_address,
        delivery_state=persistence.invoice_delivery,
    )
    released_invoice = ReleasedInvoiceService(
        persistence.billing,
        invoice_admin_delivery,
    )
    invoice_creation = InvoiceCreationService(
        InvoiceBasisService(
            persistence.billing,
            persistence.payments,
            payment_execution,
        ),
        released_invoice,
        invoice_render,
        persistence.invoice_identity,
    )

    return OnlineServices(
        projects=ProjectApplicationService(persistence.projects),
        project_pricing=(
            ProjectPricingService(
                pricing_rule,
                persistence.projects.capacity_for_customer_project,
                discount_eligibility_for_project,
            )
            if pricing_rule is not None
            else None
        ),
        project_upload=ProjectUploadService(
            persistence.uploads.store,
            persistence.projects.project_belongs_to_customer,
        ),
        project_processing=ProjectProcessingService(
            persistence.projects.project_belongs_to_customer,
            persistence.uploads.project_directory,
            import_m3t_project,
            persist_import=lambda customer_id, project_id, imported: store_project_import(
                persistence.projects, customer_id, project_id, imported
            ),
            import_project_with_heartbeat=lambda directory, heartbeat: import_m3t_project(
                directory, heartbeat=heartbeat
            ),
            persist_import_with_heartbeat=lambda customer_id, project_id, imported, heartbeat: store_project_import(
                persistence.projects, customer_id, project_id, imported, heartbeat=heartbeat
            ),
            record_state_for_request=lambda request: ComputeJobProcessingStateRecorder(
                compute_jobs,
                job_id=request.job_id or "",
                customer_id=request.customer_id,
                project_id=request.project_id,
                worker_id=f"project-processing-{uuid4().hex}",
                lease=(
                    project_processing_lease()
                    if project_processing_lease is not None
                    else None
                ),
                now=(
                    (lambda: project_processing_lease().now)
                    if project_processing_lease is not None
                    else None
                ),
                renew_lease=project_processing_lease,
            ),
        ),
        project_creation=ProjectCreationService(
            lambda project: persistence.projects.create_customer_project(
                project.customer_id,
                project.project_id,
                project.name,
                project.capacity_kwp,
            )
        ),
        registration=registration,
        login=login,
        compute_jobs=compute_jobs,
        billing=billing,
        payment_checkout=payment_checkout,
        report_delivery=report_delivery,
        report_recovery=report_recovery,
        payment_authorization=payment_authorization,
        payment_capture=payment_capture,
        payment_void=payment_void,
        sepa_checkout=sepa_checkout,
        sepa_payment=sepa_payment,
        sepa_reconciliation=sepa_reconciliation,
        payment_execution=payment_execution,
        invoice_creation=invoice_creation,
        smtp_admin=smtp_admin,
        admin_readiness=admin_readiness,
        admin=admin,
        production=production,
        entitlements=persistence.entitlements,
        credentials=persistence.credentials,
        sessions=persistence.sessions,
    )
