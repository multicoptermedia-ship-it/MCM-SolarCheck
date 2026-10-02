"""Persistent server-side dependencies for SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.infrastructure.filesystem_invoice import FileSystemInvoiceArchive
from mcm_solarcheck.infrastructure.filesystem_report import FileSystemReportArtifactStore
from mcm_solarcheck.infrastructure.online_private_paths import OnlinePrivatePaths
from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
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
from mcm_solarcheck.infrastructure.sqlite_smtp_admin_audit import SQLiteSMTPAdminAudit
from mcm_solarcheck.infrastructure.sqlite_solarcheck_tariff import SQLiteSolarCheckTariffStore
from mcm_solarcheck.infrastructure.sqlite_smtp_settings import SQLiteSMTPSettingsStore
from mcm_solarcheck.infrastructure.sqlite_voucher import SQLiteFlightPlanVoucherPolicyStore, SQLiteFlightPlanVoucherStore
from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig
from mcm_solarcheck.services.smtp_admin import SMTPSecretStore


@dataclass(frozen=True)
class OnlinePersistence:
    """Authoritative persistent dependencies shared by the online service layer."""

    registrations: SQLiteOnlineRegistrationStore
    entitlements: SQLiteOnlineEntitlementStore
    compute_jobs: SQLiteComputeJobStore
    billing: SQLiteComputeJobBillingStore
    payments: SQLiteOnlinePaymentStore
    merchant_accounts: SQLiteMerchantAccountStore
    tariffs: SQLiteSolarCheckTariffStore
    vouchers: SQLiteFlightPlanVoucherStore
    voucher_policy: SQLiteFlightPlanVoucherPolicyStore
    priced_payments: SQLitePricedPaymentStore
    payment_operations: SQLitePaymentOperationIntentStore
    payment_authorizations: SQLitePaymentAuthorizationIntentStore
    sepa_mandates: SQLiteSepaMandateStore
    sepa_submissions: SQLiteSepaSubmissionStore
    sepa_collections: SQLiteSepaCollectionStore
    invoice_identity: SQLiteInvoiceIdentityStore
    invoice_delivery: SQLiteInvoiceAdminDeliveryStore
    reports: FileSystemReportArtifactStore
    report_recovery: SQLiteReportRecoveryStore
    invoices: FileSystemInvoiceArchive
    smtp_settings: SQLiteSMTPSettingsStore
    smtp_secrets: SMTPSecretStore
    smtp_admin_audit: SQLiteSMTPAdminAudit


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
