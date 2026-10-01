"""Persistent server-side dependencies for SolarCheck Online."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.infrastructure.filesystem_invoice import FileSystemInvoiceArchive
from mcm_solarcheck.infrastructure.online_private_paths import OnlinePrivatePaths
from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.infrastructure.sqlite_invoice_admin_delivery import SQLiteInvoiceAdminDeliveryStore
from mcm_solarcheck.infrastructure.sqlite_invoice_identity import SQLiteInvoiceIdentityStore
from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_payment_operation import SQLitePaymentOperationIntentStore
from mcm_solarcheck.infrastructure.sqlite_sepa import SQLiteSepaMandateStore
from mcm_solarcheck.infrastructure.sqlite_sepa_collection import SQLiteSepaCollectionStore
from mcm_solarcheck.infrastructure.sqlite_sepa_submission import SQLiteSepaSubmissionStore


@dataclass(frozen=True)
class OnlinePersistence:
    """Authoritative persistent dependencies shared by the online service layer."""

    billing: SQLiteComputeJobBillingStore
    payments: SQLiteOnlinePaymentStore
    payment_operations: SQLitePaymentOperationIntentStore
    sepa_mandates: SQLiteSepaMandateStore
    sepa_submissions: SQLiteSepaSubmissionStore
    sepa_collections: SQLiteSepaCollectionStore
    invoice_identity: SQLiteInvoiceIdentityStore
    invoice_delivery: SQLiteInvoiceAdminDeliveryStore
    invoices: FileSystemInvoiceArchive


def build_online_persistence(paths: OnlinePrivatePaths) -> OnlinePersistence:
    """Build durable online stores only from validated private deployment paths."""
    if not isinstance(paths, OnlinePrivatePaths):
        raise TypeError("paths must be OnlinePrivatePaths")

    database = paths.state_database
    database.parent.mkdir(parents=True, exist_ok=True)
    paths.reports_root.mkdir(parents=True, exist_ok=True)
    paths.invoices_root.mkdir(parents=True, exist_ok=True)

    return OnlinePersistence(
        billing=SQLiteComputeJobBillingStore(database),
        payments=SQLiteOnlinePaymentStore(database),
        payment_operations=SQLitePaymentOperationIntentStore(database),
        sepa_mandates=SQLiteSepaMandateStore(database),
        sepa_submissions=SQLiteSepaSubmissionStore(database),
        sepa_collections=SQLiteSepaCollectionStore(database),
        invoice_identity=SQLiteInvoiceIdentityStore(database),
        invoice_delivery=SQLiteInvoiceAdminDeliveryStore(database),
        invoices=FileSystemInvoiceArchive(paths.invoices_root),
    )
