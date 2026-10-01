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
from mcm_solarcheck.services.payment_execution import PaymentExecutionEvidence
from mcm_solarcheck.services.released_invoice import ReleasedInvoiceService
from mcm_solarcheck.services.report_delivery import ReportDeliveryService
from mcm_solarcheck.services.report_recovery import ReportRecoveryService
from mcm_solarcheck.services.report_recovery_notification import ReportRecoveryNotificationService
from mcm_solarcheck.services.smtp_admin import SMTPAdminService


@dataclass(frozen=True)
class OnlineServices:
    billing: ComputeJobBillingService
    report_delivery: ReportDeliveryService
    report_recovery: ReportRecoveryService
    payment_execution: PaymentExecutionEvidence
    invoice_creation: InvoiceCreationService
    smtp_admin: SMTPAdminService


def build_online_services(
    persistence: OnlinePersistence,
    *,
    invoice_render: InvoiceRenderConfig,
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
        payment_execution=payment_execution,
        invoice_creation=invoice_creation,
        smtp_admin=smtp_admin,
    )
