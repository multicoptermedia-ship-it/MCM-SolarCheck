from __future__ import annotations

import sqlite3

import pytest

from mcm_solarcheck.infrastructure.online_persistence import build_online_persistence
from mcm_solarcheck.infrastructure.online_private_paths import OnlinePrivatePaths


def test_online_persistence_uses_one_private_state_database(tmp_path) -> None:
    private = tmp_path / "private"
    paths = OnlinePrivatePaths(
        private / "state" / "solarcheck.sqlite",
        private / "reports",
        private / "invoices",
        tmp_path / "public",
    )

    persistence = build_online_persistence(paths)

    database_backed = (
        persistence.billing,
        persistence.payments,
        persistence.payment_operations,
        persistence.sepa_mandates,
        persistence.sepa_submissions,
        persistence.sepa_collections,
        persistence.invoice_identity,
        persistence.invoice_delivery,
    )
    assert {store.database for store in database_backed} == {str(paths.state_database)}
    assert persistence.invoices.root == paths.invoices_root
    assert paths.reports_root.is_dir()
    assert paths.invoices_root.is_dir()

    with sqlite3.connect(paths.state_database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {
        "compute_job_billing",
        "online_payments",
        "payment_operation_intents",
        "sepa_mandates",
        "sepa_submissions",
        "sepa_collections",
        "invoice_identity",
        "invoice_admin_delivery",
    } <= tables


def test_online_persistence_requires_validated_private_paths(tmp_path) -> None:
    with pytest.raises(TypeError, match="OnlinePrivatePaths"):
        build_online_persistence(tmp_path)  # type: ignore[arg-type]
