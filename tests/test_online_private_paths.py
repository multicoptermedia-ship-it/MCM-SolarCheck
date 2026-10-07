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
    assert paths.uploads_root == (private / "uploads").resolve()
    assert web.resolve() not in paths.uploads_root.parents


@pytest.mark.parametrize(
    "private_path",
    ["database", "reports", "invoices", "uploads"],
)
def test_online_private_paths_reject_web_served_private_storage(
    tmp_path, private_path
) -> None:
    web = tmp_path / "public"
    database = tmp_path / "private" / "solarcheck.sqlite"
    reports = tmp_path / "private" / "reports"
    invoices = tmp_path / "private" / "invoices"
    uploads = tmp_path / "private" / "uploads"

    if private_path == "database":
        database = web / "solarcheck.sqlite"
    elif private_path == "reports":
        reports = web / "reports"
    elif private_path == "invoices":
        invoices = web / "invoices"
    else:
        uploads = web / "uploads"

    with pytest.raises(ValueError, match="outside web root"):
        OnlinePrivatePaths(database, reports, invoices, web, uploads)


def test_online_private_paths_reject_overlapping_report_and_invoice_roots(tmp_path) -> None:
    private = tmp_path / "private"

    with pytest.raises(ValueError, match="separate directories"):
        OnlinePrivatePaths(
            private / "solarcheck.sqlite",
            private / "documents",
            private / "documents" / "invoices",
        )


def test_online_private_paths_reject_overlapping_upload_storage(tmp_path) -> None:
    private = tmp_path / "private"

    with pytest.raises(ValueError, match="separate directories"):
        OnlinePrivatePaths(
            private / "solarcheck.sqlite",
            private / "reports",
            private / "invoices",
            uploads_root=private / "reports" / "uploads",
        )


def test_online_private_paths_reject_web_root_inside_reports(tmp_path) -> None:
    private = tmp_path / "private"

    with pytest.raises(ValueError, match="separate from web root"):
        OnlinePrivatePaths(
            private / "solarcheck.sqlite",
            private / "reports",
            private / "invoices",
            private / "reports" / "public",
        )


def test_online_private_paths_reject_web_root_inside_invoices(tmp_path) -> None:
    private = tmp_path / "private"

    with pytest.raises(ValueError, match="separate from web root"):
        OnlinePrivatePaths(
            private / "solarcheck.sqlite",
            private / "reports",
            private / "invoices",
            private / "invoices" / "public",
        )
