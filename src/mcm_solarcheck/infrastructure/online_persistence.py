"""Persistent server-side dependencies for SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.infrastructure.filesystem_invoice import FileSystemInvoiceArchive
from mcm_solarcheck.infrastructure.filesystem_report import FileSystemReportArtifactStore
from mcm_solarcheck.infrastructure.online_private_paths import OnlinePrivatePaths
from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
from mcm_solarcheck.infrastructure.sqlite_credentials import SQLiteCredentialStore
from mcm_solarcheck.infrastructure.sqlite_invoice_admin_delivery import SQLiteInvoiceAdminDeliveryStore
from mcm_solarcheck.infrastructure.sqlite_invoice_identity import SQLiteInvoiceIdentityStore
from mcm_solarcheck.infrastructure.sqlite_merchant_account import SQLiteMerchantAccountStore
from mcm_solarcheck.infrastructure.sqlite_online_entitlement import SQLiteOnlineEntitlementStore
from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_payment_authorization import SQLitePaymentAuthorizationIntentStore
from mcm_solarcheck.infrastructure.sqlite_payment_operation import SQLitePaymentOperationIntentStore
from mcm_solarcheck.infrastructure.sqlite_priced_payment import SQLitePricedPaymentStore
from mcm_solarcheck.infrastructure.sqlite_report_recovery import SQLiteReportRecoveryStore
from mcm_solarcheck.infrastructure.sqlite_registration import SQLiteOnlineRegistrationStore
from mcm_solarcheck.infrastructure.sqlite_sepa import SQLiteSepaMandateStore
from mcm_solarcheck.infrastructure.sqlite_sepa_collection import SQLiteSepaCollectionStore
from mcm_solarcheck.infrastructure.sqlite_sepa_submission import SQLiteSepaSubmissionStore
from mcm_solarcheck.infrastructure.sqlite_session import SQLiteSessionStore
from mcm_solarcheck.infrastructure.sqlite_smtp_admin_audit import SQLiteSMTPAdminAudit
from mcm_solarcheck.infrastructure.sqlite_solarcheck_tariff import SQLiteSolarCheckTariffStore
from mcm_solarcheck.infrastructure.sqlite_smtp_settings import SQLiteSMTPSettingsStore
from mcm_solarcheck.infrastructure.sqlite_voucher import SQLiteFlightPlanVoucherPolicyStore, SQLiteFlightPlanVoucherStore
from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig
from mcm_solarcheck.services.billing import ComputeJobBillingStore
from mcm_solarcheck.services.invoice_creation import InvoiceIdentityStore
from mcm_solarcheck.services.invoice_admin_delivery import InvoiceAdminDeliveryStateStore, InvoiceArchive
from mcm_solarcheck.services.report_delivery import ReportArtifactStore
from mcm_solarcheck.services.report_recovery import ReportRecoveryClaimStore
from mcm_solarcheck.services.compute_jobs import OnlineComputeJobPersistence
from mcm_solarcheck.services.merchant_account import MerchantAccountPersistence
from mcm_solarcheck.services.online_credentials import CredentialStore
from mcm_solarcheck.services.online_entitlement import OnlineEntitlementStore
from mcm_solarcheck.services.payment import OnlinePaymentPersistence
from mcm_solarcheck.services.payment_authorization_intent import PaymentAuthorizationIntentStore
from mcm_solarcheck.services.payment_operation import PaymentOperationIntentStore
from mcm_solarcheck.services.solarcheck_tariff import SolarCheckTariffPersistence
from mcm_solarcheck.services.payment_pricing import AtomicPricedPaymentStore
from mcm_solarcheck.services.voucher import FlightPlanVoucherPersistence
from mcm_solarcheck.services.voucher_admin import FlightPlanVoucherPolicyPersistence
from mcm_solarcheck.services.online_registration import OnlineRegistrationStore
from mcm_solarcheck.services.online_session import SessionStore
from mcm_solarcheck.services.smtp_admin import SMTPAdminAudit, SMTPSecretStore, SMTPSettingsStore
from mcm_solarcheck.services.sepa import SepaMandatePersistence
from mcm_solarcheck.services.sepa_submission import SepaSubmissionPersistence
from mcm_solarcheck.services.sepa_collection import SepaCollectionPersistence


@dataclass(frozen=True)
class OnlinePersistence:
    """Provider-neutral persistent dependencies shared by the online service layer.\n\n    Concrete SQLite stores are assembled by ``build_online_persistence`` today.\n    The dependency container deliberately does not expose SQLite-specific types so a\n    production MySQL adapter can satisfy the same service-layer boundary later.\n    """

    registrations: OnlineRegistrationStore
    credentials: CredentialStore
    sessions: SessionStore
    entitlements: OnlineEntitlementStore
    compute_jobs: OnlineComputeJobPersistence
    billing: ComputeJobBillingStore
    payments: OnlinePaymentPersistence
    merchant_accounts: MerchantAccountPersistence
    tariffs: SolarCheckTariffPersistence
    vouchers: FlightPlanVoucherPersistence
    voucher_policy: FlightPlanVoucherPolicyPersistence
    priced_payments: AtomicPricedPaymentStore
    payment_operations: PaymentOperationIntentStore
    payment_authorizations: PaymentAuthorizationIntentStore
    sepa_mandates: SepaMandatePersistence
    sepa_submissions: SepaSubmissionPersistence
    sepa_collections: SepaCollectionPersistence
    invoice_identity: InvoiceIdentityStore
    invoice_delivery: InvoiceAdminDeliveryStateStore
    reports: ReportArtifactStore
    report_recovery: ReportRecoveryClaimStore
    invoices: InvoiceArchive
    smtp_settings: SMTPSettingsStore
    smtp_secrets: SMTPSecretStore
    smtp_admin_audit: SMTPAdminAudit


def build_online_persistence(
    paths: OnlinePrivatePaths,
    *,
    smtp_default: SMTPConfig,
    smtp_secrets: SMTPSecretStore,
) -> OnlinePersistence:
    """Build durable online stores only from validated private deployment paths."""
    if not isinstance(paths, OnlinePrivatePaths):
        raise TypeError("paths must be OnlinePrivatePaths")
    if not isinstance(smtp_default, SMTPConfig):
        raise TypeError("smtp_default must be SMTPConfig")

    database = paths.state_database
    database.parent.mkdir(parents=True, exist_ok=True)
    paths.reports_root.mkdir(parents=True, exist_ok=True)
    paths.invoices_root.mkdir(parents=True, exist_ok=True)

    payments = SQLiteOnlinePaymentStore(database)
    vouchers = SQLiteFlightPlanVoucherStore(database)
    voucher_policy = SQLiteFlightPlanVoucherPolicyStore(database)
    voucher_policy.bootstrap_default()
    return OnlinePersistence(
        registrations=SQLiteOnlineRegistrationStore(database),
        credentials=SQLiteCredentialStore(database),
        sessions=SQLiteSessionStore(database),
        entitlements=SQLiteOnlineEntitlementStore(database),
        compute_jobs=SQLiteComputeJobStore(database),
        billing=SQLiteComputeJobBillingStore(database),
        payments=payments,
        merchant_accounts=SQLiteMerchantAccountStore(database),
        tariffs=SQLiteSolarCheckTariffStore(database),
        vouchers=vouchers,
        voucher_policy=voucher_policy,
        priced_payments=SQLitePricedPaymentStore(database, database),
        payment_operations=SQLitePaymentOperationIntentStore(database),
        payment_authorizations=SQLitePaymentAuthorizationIntentStore(database),
        sepa_mandates=SQLiteSepaMandateStore(database),
        sepa_submissions=SQLiteSepaSubmissionStore(database),
        sepa_collections=SQLiteSepaCollectionStore(database),
        invoice_identity=SQLiteInvoiceIdentityStore(database),
        invoice_delivery=SQLiteInvoiceAdminDeliveryStore(database),
        reports=FileSystemReportArtifactStore(paths.reports_root),
        report_recovery=SQLiteReportRecoveryStore(database),
        invoices=FileSystemInvoiceArchive(paths.invoices_root),
        smtp_settings=SQLiteSMTPSettingsStore(database, smtp_default),
        smtp_secrets=smtp_secrets,
        smtp_admin_audit=SQLiteSMTPAdminAudit(database),
    )
