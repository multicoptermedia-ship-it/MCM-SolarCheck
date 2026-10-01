"""Provider-neutral service composition for SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.infrastructure.online_persistence import OnlinePersistence
from mcm_solarcheck.infrastructure.smtp_email import SMTPEmailSender
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.email import ReportRecoveryEmailConfig
from mcm_solarcheck.services.invoice import InvoiceBasisService
from mcm_solarcheck.services.invoice_admin_delivery import InvoiceAdminDeliveryService
from mcm_solarcheck.services.invoice_creation import InvoiceCreationService, InvoiceRenderConfig
from mcm_solarcheck.services.online_admin_readiness import (
    ConfigurationReadiness,
    OnlineAdminReadinessService,
)
from mcm_solarcheck.services.payment_capture import PaymentCaptureService
from mcm_solarcheck.services.payment_execution import PaymentExecutionEvidence
from mcm_solarcheck.services.payment_gateway import PaymentAuthorizationService, PaymentGateway
from mcm_solarcheck.services.payment_void import PaymentVoidService
from mcm_solarcheck.services.released_invoice import ReleasedInvoiceService
from mcm_solarcheck.services.report_delivery import ReportDeliveryService
from mcm_solarcheck.services.report_recovery import ReportRecoveryService
from mcm_solarcheck.services.report_recovery_notification import ReportRecoveryNotificationService
from mcm_solarcheck.services.sepa_payment import SepaPaymentGateway, SepaPaymentService
from mcm_solarcheck.services.smtp_admin import SMTPAdminService


@dataclass(frozen=True)
class OnlineServices:
    billing: ComputeJobBillingService
    report_delivery: ReportDeliveryService
    report_recovery: ReportRecoveryService
    payment_authorization: PaymentAuthorizationService
    payment_capture: PaymentCaptureService
    payment_void: PaymentVoidService
    sepa_payment: SepaPaymentService
    payment_execution: PaymentExecutionEvidence
    invoice_creation: InvoiceCreationService
    smtp_admin: SMTPAdminService
    admin_readiness: OnlineAdminReadinessService


def build_online_services(
    persistence: OnlinePersistence,
    *,
    invoice_render: InvoiceRenderConfig,
    payment_gateway: PaymentGateway,
    sepa_gateway: SepaPaymentGateway,
    sepa_provider_id: str,
    payment_provider_readiness: ConfigurationReadiness,
    sepa_provider_readiness: ConfigurationReadiness,
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

    billing = ComputeJobBillingService(persistence.billing)
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
    )

    payment_authorization = PaymentAuthorizationService(
        persistence.payments,
        payment_gateway,
        intents=persistence.payment_authorizations,
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
    sepa_payment = SepaPaymentService(
        persistence.payments,
        persistence.sepa_mandates,
        sepa_gateway,
        sepa_provider_id,
        collections=persistence.sepa_collections,
        submissions=persistence.sepa_submissions,
        billing=persistence.billing,
    )
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
        billing=billing,
        report_delivery=report_delivery,
        report_recovery=report_recovery,
        payment_authorization=payment_authorization,
        payment_capture=payment_capture,
        payment_void=payment_void,
        sepa_payment=sepa_payment,
        payment_execution=payment_execution,
        invoice_creation=invoice_creation,
        smtp_admin=smtp_admin,
        admin_readiness=admin_readiness,
    )
