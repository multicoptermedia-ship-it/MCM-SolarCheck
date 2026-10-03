from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.online_private_paths import OnlinePrivatePaths


def test_online_private_paths_keep_documents_outside_web_root(tmp_path) -> None:
    web = tmp_path / "public"
    private = tmp_path / "private"

    paths = OnlinePrivatePaths(
        private / "solarcheck.sqlite",
        private / "reports",
        private / "invoices",
        web,
    )

    assert paths.reports_root != paths.invoices_root
    assert web.resolve() not in paths.reports_root.parents
    assert web.resolve() not in paths.invoices_root.parents


@pytest.mark.parametrize(
    "private_path",
    ["database", "reports", "invoices"],
)
def test_online_private_paths_reject_web_served_private_storage(
    tmp_path, private_path
) -> None:
    web = tmp_path / "public"
    database = tmp_path / "private" / "solarcheck.sqlite"
    reports = tmp_path / "private" / "reports"
    invoices = tmp_path / "private" / "invoices"

    if private_path == "database":
        database = web / "solarcheck.sqlite"
    elif private_path == "reports":
        reports = web / "reports"
    else:
        invoices = web / "invoices"

    with pytest.raises(ValueError, match="outside web root"):
        OnlinePrivatePaths(database, reports, invoices, web)


def test_online_private_paths_reject_overlapping_report_and_invoice_roots(tmp_path) -> None:
    private = tmp_path / "private"

    with pytest.raises(ValueError, match="separate directories"):
        OnlinePrivatePaths(
            private / "solarcheck.sqlite",
            private / "documents",
            private / "documents" / "invoices",
        )
